import re
import numpy as np
from scipy.sparse import csr_matrix
from sparse_dot_topn import sparse_dot_topn as ct
from sklearn.feature_extraction.text import TfidfVectorizer

import numpy as np
import pandas as pd

import string
import time
import re

def split_string_1(column):
    if re.search(r'\bt/a\b',str(column).lower()) is not None:
        new_name = column.lower().split('t/a')[-1].strip()
    elif re.search(r'\bh/a\b',str(column).lower()) is not None:
        new_name = column.lower().split('h/a')[-1].strip()
    else:
        new_name = 'ABCXYZ'
    
    if len(new_name)<1:
        new_name = 'ABCXYZ'
    return new_name

#Take the first piece of the trading as split
def split_string_2(column):
    if re.search(r'\bt/a\b',str(column).lower()) is not None:
        new_name = column.lower().split('t/a')[0].strip()
    elif re.search(r'\bh/a\b',str(column).lower()) is not None:
        new_name = column.lower().split('h/a')[0].strip()
    else:
        new_name = 'ABCXYZ'
        
    if len(new_name)<1:
        new_name = 'ABCXYZ'
        
    return new_name
    
def split_cols(df,df_col):    
     for i in range(len(df_col)):
        #print('Now running for '+df_col[i])    
        g = 'Trading_as_name_'+str(i)+'_1'
        h = 'Trading_as_name_'+str(i)+'_2'
        df[g] = df[df_col[i]].apply(lambda x: split_string_1(x))
        df[h] = df[df_col[i]].apply(lambda x: split_string_2(x))
     return df
	 
#Cosine similarity function
def awesome_cossim_top(A, B, ntop, lower_bound=0):
    # force A and B as a CSR matrix.
    # If they have already been CSR, there is no overhead
    A = A.tocsr()
    B = B.tocsr()
    M, _ = A.shape
    _, N = B.shape
 
    idx_dtype = np.int32
 
    nnz_max = M*ntop
 
    indptr = np.zeros(M+1, dtype=idx_dtype)
    indices = np.zeros(nnz_max, dtype=idx_dtype)
    data = np.zeros(nnz_max, dtype=A.dtype)

    ct.sparse_dot_topn(
        M, N, np.asarray(A.indptr, dtype=idx_dtype),
        np.asarray(A.indices, dtype=idx_dtype),
        A.data,
        np.asarray(B.indptr, dtype=idx_dtype),
        np.asarray(B.indices, dtype=idx_dtype),
        B.data,
        ntop,
        lower_bound,
        indptr, indices, data)

    return csr_matrix((data,indices,indptr),shape=(M,N))

#Ngrams function
def ngrams(word, n=3):
    word = [char for char in word if char not in string.punctuation]#remove puntuation from the string
    word = ''.join(word)
    ngrams = zip(*[word[i:] for i in range(n)])
    return[''.join(ngram) for ngram in ngrams]

#Function for getting the names that match
def get_matches_df(sparse_matrix, name_vector):
    non_zeros = sparse_matrix.nonzero()
    
    sparserows = non_zeros[0]
    sparsecols = non_zeros[1]
    
    #if top:
    #    nr_matches = top
    #else:
    nr_matches = sparsecols.size
    
    left_side = np.empty([nr_matches], dtype=object)
    right_side = np.empty([nr_matches], dtype=object)
    similairity = np.zeros(nr_matches)
    
    for index in range(0, nr_matches):
        left_side[index] = name_vector[sparserows[index]]
        right_side[index] = name_vector[sparsecols[index]]
        similairity[index] = sparse_matrix.data[index]
    
    return pd.DataFrame({'left_side': left_side,
                          'right_side': right_side,
                           'similarity': similairity})
