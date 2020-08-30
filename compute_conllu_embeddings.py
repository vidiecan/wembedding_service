#!/usr/bin/env python3
#
# Copyright 2020 Institute of Formal and Applied Linguistics, Faculty of
# Mathematics and Physics, Charles University, Czech Republic.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import sys
import zipfile

import numpy as np
import tensorflow as tf

import wembeddings.wembeddings as wembeddings

if __name__ == "__main__":
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("input_conllu", type=str, help="Input CoNLL-U file")
    parser.add_argument("output_npz", type=str, help="Output NPZ file")
    parser.add_argument("--batch_size", default=64, type=int, help="Batch size")
    parser.add_argument("--dtype", default="float16", type=str, help="Dtype to save as")
    parser.add_argument("--model", default="bert-base-multilingual-uncased-last4", type=str, help="Model name (see wembeddings.py for options)")
    parser.add_argument("--threads", default=4, type=int, help="Threads to use")
    args = parser.parse_args()

    args.dtype = getattr(np, args.dtype)

    # Impose the limit on the number of threads
    tf.config.threading.set_inter_op_parallelism_threads(args.threads)
    tf.config.threading.set_intra_op_parallelism_threads(args.threads)

    # Load CoNLL-U file
    sentences = []
    with open(args.input_conllu, mode="r", encoding="utf-8") as conllu_file:
        in_sentence = False
        for line in conllu_file:
            line = line.rstrip("\n")
            if line:
                if not in_sentence:
                    sentences.append([])
                    in_sentence = True
                if re.match(r"^[0-9]*\t", line):
                    columns = line.split("\t")
                    assert len(columns) == 10
                    sentences[-1].append(columns[1])
            else:
                in_sentence = False
            if line.startswith("#"): continue
    print("Loaded CoNLL-U file with {} sentences and {} words.".format(len(sentences), sum(map(len, sentences))), file=sys.stderr, flush=True)

    # Compute word embeddings
    wembeddings = wembeddings.WEmbeddings(models_map={args.model: wembeddings.WEmbeddings.MODELS_MAP[args.model]})
    with zipfile.ZipFile(args.output_npz, mode="w", compression=zipfile.ZIP_STORED) as output_npz:
        for i in range(0, len(sentences), args.batch_size):
            sentences_embeddings = wembeddings.compute_embeddings(args.model, sentences[i:i + args.batch_size])
            for j, sentence_embeddings in enumerate(sentences_embeddings):
                with output_npz.open("arr_{}".format(i + j), mode="w") as embeddings_file:
                    np.save(embeddings_file, sentence_embeddings.astype(args.dtype))
                if (i + j + 1) % 100 == 0:
                    print("Processed {}/{} sentences.".format(i + j + 1, len(sentences)), file=sys.stderr, flush=True)
    print("Done, all embeddings saved.", file=sys.stderr, flush=True)