#!/usr/bin/env python

import argparse
import codecs
import os
import numpy

import mplm_context as mplm
import symbol_table as st

parser = argparse.ArgumentParser()
parser.add_argument('--network_dir', default="/usr1/home/ytsvetko/projects/mnlm/work/context")
parser.add_argument('--lang_list', default="ar")
parser.add_argument('--symbol_table', default="/usr1/home/ytsvetko/projects/mnlm/work/symbol_table.en_ru_fr_ro_it_mt_sw_hi_ar")
parser.add_argument('--dev_path', default="/usr1/home/ytsvetko/projects/mnlm/data/pron/dev/pron-dict.ar")
parser.add_argument('--test_path', default="/usr1/home/ytsvetko/projects/mnlm/data/pron/test/pron-dict.ar")
parser.add_argument('--vector_size', type=int, default=100)
parser.add_argument('--context_size', type=int, default=2)
parser.add_argument('--batch_size', type=int, default=100)
parser.add_argument('--alpha', type=float, default=1.0)
parser.add_argument('--betta', type=float, default=0.0)
args = parser.parse_args()

start_symbol = "<s>"
end_symbol = "</s>"

insert_symbol = "INS"
delete_symbol = "DEL"


def LoadData(corpus, symbol_table, context_size, lang):
  # in format: text corpus, embeddings, n-gram order
  # out format: for each n-gram, x: n-1 embeddings appended; y: n's word 1-hot representation
  lang_symbol = symbol_table.WordIndex(lang)
  x = []
  y = []
  lang_symbols = []
  def next_ngram(corpus):
    for line in codecs.open(corpus, "r", "utf-8"):
      tokens = line.split()
      #pad with boundary tokens
      tokens = [start_symbol]*context_size + tokens + [end_symbol]*context_size
      for ngram in zip(*[tokens[i:] for i in range(1+context_size*2)]):
        yield ngram
       
  for ngram in next_ngram(corpus):
    x.append([symbol_table.WordIndex(word) for word in ngram[:context_size]] +
             [symbol_table.WordIndex(insert_symbol)] +
             [symbol_table.WordIndex(word) for word in ngram[context_size+1:]] + 
             [lang_symbol])
    y.append(symbol_table.WordIndex(ngram[context_size]))
    lang_symbols.append(lang_symbol)

  return x, y, lang_symbols


def SaveVectors(symbol_table, vector_matrix, filename):
  out_f = codecs.open(filename, "w", "utf-8")
  for i, vector in enumerate(vector_matrix):
    vector = [str(num) for num in vector]
    out_f.write(u"{} {}\n".format(symbol_table.IndexToWord(i), " ".join(vector)))

def AppendLangData(symbol_table, context_size, corpus_filename, 
                   x, y, lang, lang_symbols):
  x_lang, y_lang, lang_symbols_lang = LoadData(corpus_filename, symbol_table, context_size, lang)
  if x is None:
    return numpy.array(x_lang), numpy.array(y_lang), numpy.array(lang_symbols_lang)
  else:
    x = numpy.concatenate((x, x_lang), axis=0)
    y = numpy.concatenate((y, y_lang), axis=0)
    lang_symbols = numpy.concatenate((lang_symbols, lang_symbols_lang), axis=0)
    return x, y, lang_symbols
  
def GetLanguageList(languages, symbol_table):
  return numpy.array([symbol_table.WordIndex(l) for l in languages])

def main():
    
  symbol_table = st.SymbolTable()
  if os.path.exists(args.symbol_table):
    symbol_table.LoadFromFile(args.symbol_table)
    
  dev_x, dev_y, dev_lang_feat = None, None, None
  test_x, test_y, test_lang_feat = None, None, None
  for lang in args.lang_list.split("_"):
    print "Language:", lang
    if args.dev_path:
      dev_x, dev_y, dev_lang_feat = AppendLangData(
          symbol_table, args.context_size, args.dev_path,
          dev_x, dev_y, lang, dev_lang_feat)
    if args.test_path:
      test_x, test_y, test_lang_feat = AppendLangData(
          symbol_table, args.context_size, args.test_path,
          test_x, test_y, lang, test_lang_feat)

  all_lang_symbol_indexes = GetLanguageList(args.symbol_table.split(".")[-1].split("_"), symbol_table)
  network = mplm.MNLM(symbol_table.Size(), args.vector_size, 2+args.context_size*2, all_lang_symbol_indexes)
  
  network.LoadModel(args.network_dir)
  
  if args.dev_path:
    print "Dev set evaluation"
    dev_logp, dev_ppl = network.Test(dev_x, dev_y, dev_lang_feat)
    print "Dev cost mean:", dev_logp, "perplexity:", dev_ppl

  if args.test_path:
    print "Test set evaluation"
    test_logp, test_ppl = network.Test(test_x, test_y, test_lang_feat)
    print "Test cost mean:", test_logp, "perplexity:", test_ppl


if __name__ == '__main__':
    main()