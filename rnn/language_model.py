import tensorflow as tf
import numpy as np
import nltk
import csv
import os

features = []
inv_features = {}
sentiment_lookup = ['anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise']

def read_test(file_location, rows_to_take = -1):
    global features, inv_features
    with open(file_location, 'rb') as data:
        data_reader = csv.DictReader(data)
        data_reader = list(data_reader)

        if rows_to_take == -1:
            rows_to_take = len(data_reader)

        y = np.empty((18, rows_to_take, 1))
        x = np.empty((18, rows_to_take, 1))

        i = 0

        for row in data_reader:
            h_tokens = nltk.word_tokenize(row['headline'].lower())
            y[:, i, 0] = (float(row[' anger']),
                          float(row[' disgust']),
                          float(row[' fear']),
                          float(row[' joy']),
                          float(row[' sadness']),
                          float(row[' surprise']),
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

            f_vector = []
            for token in h_tokens:
                if token in inv_features:
                    f_vector.append(inv_features[token])
                else:
                    f_vector.append(-1)

            while (len(f_vector) < 18):
                f_vector.append(-2)

            x[:, i, 0] = f_vector
            i+=1

        return x,y

def compute_input_vec(headline):
    h_tokens = nltk.word_tokenize(headline.lower())

    x = np.empty((18, 1, 1))

    f_vector = []
    for token in h_tokens:
        if token in inv_features:
            f_vector.append(inv_features[token])
        else:
            f_vector.append(-1)

    while (len(f_vector) < 18):
        f_vector.append(-2)

    x[:,0,0] = f_vector

    return x


def read_csv(file_location, rows_to_take = -1):
    raw_data = []
    training_data = []
    word_freq = {}
    max_len = 0

    with open(file_location, 'rb') as data:
        data_reader = csv.DictReader(data)
        data_reader = list(data_reader)

        if rows_to_take == -1:
            rows_to_take = len(data_reader)

        y = np.empty((18, rows_to_take, 1))

        i = 0

        for row in data_reader:
            h_tokens = nltk.word_tokenize(row['headline'].lower())

            max_len = max(max_len, len(h_tokens))

            for token in h_tokens:
                if token in word_freq:
                    word_freq[token] += 1
                else:
                    word_freq[token] = 1

            y[:, i, 0] = (float(row[' anger']),
                          float(row[' disgust']),
                          float(row[' fear']),
                          float(row[' joy']),
                          float(row[' sadness']),
                          float(row[' surprise']),
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

            raw_data.append(h_tokens)
            i+=1

        x = np.empty((max_len, rows_to_take, 1))

        #print len(raw_data)
        #print rows_to_take

        global features
        global inv_features
        features = sorted(word_freq.keys(), key=word_freq.get)[-1000:]
        inv_features = {}

        for i in xrange(len(features)):
            inv_features[features[i]] = i

        for i in xrange(rows_to_take):
            f_vector = []
            for token in raw_data[i]:
                if token in inv_features:
                    f_vector.append(inv_features[token])
                else:
                    f_vector.append(-1)

            while len(f_vector) < max_len:
                f_vector.append(-2)

            #print f_vector

            x[:, i, 0] = f_vector

        return x, y

INPUT_SZ = 1
OUTPUT_SZ = 1
RNN_HIDDEN = 100
EPSILON = 1e-6
ALPHA = 0.0005

inputs = tf.placeholder(tf.float32, (None, None, INPUT_SZ))
outputs = tf.placeholder(tf.float32, (None, None, OUTPUT_SZ))

cell = tf.contrib.rnn.BasicRNNCell(RNN_HIDDEN)

batch_size = tf.shape(inputs)[1]
initial_state = cell.zero_state(batch_size, tf.float32)

rnn_outputs, rnn_states = tf.nn.dynamic_rnn(cell, inputs,
        initial_state=initial_state, time_major=True)

final_projection = lambda x: tf.contrib.layers.linear(x, num_outputs=OUTPUT_SZ,
        activation_fn=tf.nn.sigmoid)

predicted_outputs = tf.map_fn(final_projection, rnn_outputs)

#error = -(outputs * tf.log(predicted_outputs + EPSILON) + (1.0 - outputs) * tf.log(1.0 - predicted_outputs + EPSILON))
error = tf.norm(outputs - predicted_outputs) + EPSILON
error = tf.reduce_mean(error)

train_fn = tf.train.AdamOptimizer(learning_rate=ALPHA).minimize(error)

#accuracy = tf.reduce_mean(tf.cast(tf.abs(outputs - predicted_dhfutputs) < 0.5, tf.float32))
accuracy = tf.reduce_mean(tf.norm(outputs - predicted_outputs))
#accuracy = calculate_accuracy(outputs, predicted_outputs)

session = tf.Session()

session.run(tf.global_variables_initializer())

x, y = read_csv("../emotion_data_train.csv")
xt, yt = read_test("../emotion_data_test.csv")

for epoch in range(1000):
    epoch_error = 0
    for i in range(20):
        epoch_error += session.run([error, train_fn], {
            inputs: x[:, i*50:(i+1)*50, :],
            outputs: y[:, i*50:(i+1)*50, :]
            })[0]
        #print i
        # split into 20 mini batches

    epoch_error /= 1000

    valid_accuracy = session.run(accuracy, {
        inputs:  xt,
        outputs: yt,
    })

    print "Epoch %d, train error: %.2f, valid accuracy: %.1f %%" % (epoch, epoch_error, valid_accuracy * 100.0)

xt, yt = read_test("../emotion_data_test2.csv")

yp = session.run(predicted_outputs, {inputs: xt})

# redefine accuracy as interperted by HeadlineSentiment.py
def calculate_accuracy(y, yp):
# calculates the accuracy from y (correct output) of yp (projected output)
    correct = 0.0
    total = y.shape[1]

    for i in xrange(total):
        c_vec = y[:, i, 0][:6]
        p_vec = yp[:, i, 0][:6]

        #print y[:, i, 0]
        #print yp[:, i, 0]

        acceptabe_vals = []

        for i in xrange(len(c_vec)):
            if c_vec[i] > 1:
                acceptabe_vals.append(i)

        #print acceptabe_vals

        acceptabe_vals = sorted(acceptabe_vals, reverse=True,
                key=lambda x: c_vec[x])[:3]

        #print acceptabe_vals

        max_p = -1
        max_i = -1
        for i in xrange(len(p_vec)):
            if (p_vec[i] > max_p):
                max_i = i
                max_p = p_vec[i]

        if max_i in acceptabe_vals:
            correct+=1

    return correct / total

print "Accuracy: %f" % (calculate_accuracy(yt, yp))

input = raw_input()

while input != "exit":
    x = compute_input_vec(input)
    get_index = tf.arg_max(tf.reshape(predicted_outputs, [-1]), 0)
    i = session.run(get_index, {inputs:x})
    print input
    try:
        print sentiment_lookup[i]
    except IndexError:
        print "Error..."

    input = raw_input()
