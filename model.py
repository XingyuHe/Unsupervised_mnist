import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import numpy as np
import os


def conv2d(X, W, strides=None, padding='SAME'):
    if strides is None:
        strides = [1, 1, 1, 1]

    return tf.nn.conv2d(X, W, strides=strides, padding=padding)


def max_pool(X, ksize=None, strides=None, padding='SAME'):
    if ksize is None:
        ksize = [1, 2, 2, 1]

    if strides is None:
        strides = [1, 2, 2, 1]

    output, switches = tf.nn.max_pool_with_argmax(X, ksize=ksize, strides=strides,
                                                  padding=padding, name='maxpool')
    return output, switches

def xavier_init(shape, name='', uniform=True):
    num_input = sum(shape[:-1])
    num_output = shape[-1]

    if uniform:
        init_range = tf.sqrt(6.0 / (num_input + num_output))
        init_value = tf.random_uniform_initializer(-init_range, init_range)
    else:
        stddev = tf.sqrt(3.0 / (num_input + num_output))
        init_value = tf.truncated_normal_initializer(stddev=stddev)

    return tf.get_variable(name, shape=shape, initializer=init_value)

def build_cnn_layer(X, W, p_dropout=1., pool=True, reshape=None):
    L = tf.nn.relu(conv2d(X, W), name="Relu")

    if pool is True:
        L, switches = max_pool(L)

    if reshape is not None:
        L = tf.reshape(L, reshape)

    if p_dropout == 1:
        return L, switches
    else:
        return tf.nn.dropout(L, p_dropout), switches

# define model
def build_cnn_model(p_keep_conv=1., p_keep_hidden=1.):

    X = tf.placeholder(dtype=tf.float32, shape=[None, 28, 28, 1])

    W1 = xavier_init([3, 3, 1, 32], 'W1')
    W2 = xavier_init([3, 3, 32, 64], 'W2')
    W3 = xavier_init([3, 3, 64, 128], 'W3')
    W4 = xavier_init([128 * 4 * 4, 625], 'W4')
    W5 = xavier_init([625, 10], 'W5')

    with tf.name_scope('layer1') as scope:
        # L1 Conv shape=(?, 28, 28, 32)
        #    Pool     ->(?, 14, 14, 32)
        L1, switch1 = build_cnn_layer(X, W1, p_keep_conv)
    with tf.name_scope('layer2') as scope:
        # L2 Conv shape=(?, 14, 14, 64)
        #    Pool     ->(?, 7, 7, 64)
        L2, switch2 = build_cnn_layer(L1, W2, p_keep_conv)
    with tf.name_scope('layer3') as scope:
        # L3 Conv shape=(?, 7, 7, 128)
        #    Pool     ->(?, 4, 4, 128)
        #    Reshape  ->(?, 625)
        reshape = [-1, W4.get_shape().as_list()[0]]
        L3, switch3 = build_cnn_layer(L2, W3, p_keep_conv, reshape=reshape)
    with tf.name_scope('layer4') as scope:
        # L4 FC 4x4x128 inputs -> 625 outputs
        L4 = tf.nn.relu(tf.matmul(L3, W4))
        L4 = tf.nn.dropout(L4, p_keep_hidden)

    # Output(labels) FC 625 inputs -> 10 outputs
    with tf.name_scope('layer5') as scope:
        L5 = tf.matmul(L4, W5, name='model')
        output = tf.nn.softmax(L5, name='output')

    return X, output

def load_model(sess):

    saver = tf.train.Saver()
    saver.restore(sess, "./models/mnist-cnn")

def load_data():

    mnist = input_data.read_data_sets("./MNIST-data/")
    X = mnist.test.images.reshape(-1, 28, 28, 1)
    Y = mnist.test.labels

    return X, Y

def check_accuracy(X, Y, input, labels, sess):
    check_prediction = tf.equal(tf.argmax(Y, 1), labels)
    accuracy = tf.reduce_mean(tf.cast(check_prediction, tf.float32))
    accuracy_rates = sess.run(accuracy, feed_dict={X: input})

    return accuracy_rates


def non_linear_deconv(Relu, W1):

    print(Relu.shape)
    Relu = tf.reshape(Relu, [-1, 28, 28, 32])
    print(Relu.shape)
    print(W1.shape)

    zero_relu = np.zeros_like(Relu)

    zero_relu[0,0,0] = Relu[0,0,0]

    relu_back = tf.nn.relu(zero_relu)

    deconv = tf.nn.conv2d_transpose(relu_back, W1, [1, 28, 28, 1], strides=[1, 1, 1, 1])

    return deconv

def unravel_argmax(argmax, shape, output_list=[]):


    if len(shape) == 2:
        print("return")
        output_list.append(argmax // shape[-1])
        output_list.append(argmax % shape[-1])
        result = tf.stack(output_list)
        print(result.shape)
        return result

    print(shape)
    print(tf.stack(output_list).shape)

    output_list.append(argmax // shape[-1])
    return unravel_argmax(argmax % shape[-1], shape[:-1], output_list)

def unpool(prev_layer, pooling_layer, switches):

    unpooled = tf.Variable(initial_value=tf.zeros_like(prev_layer))

    print(switches[0, 0, 0, 0])

    switches = unravel_argmax(switches, prev_layer.get_shape().as_list())

    print(switches)
    print(switches.shape)
    print(switches[:,0,0,0,0])

    pooling_layer_shape = pooling_layer.shape
    for instance in range(pooling_layer_shape[0]):
        for height in range(pooling_layer_shape[1]):
            for width in range(pooling_layer_shape[2]):
                for channel in range(pooling_layer_shape[3]):
                    # print(instance * height * width * channel)
                    index = switches[:, instance, height, width, channel]
                    max_value = pooling_layer[instance, height, width, channel]
                    tf.scatter_update(unpooled, tf.reverse(index, [-1]), updates=tf.convert_to_tensor(max_value))

    return unpooled

def main(argv):

    with tf.Session() as sess:

        X, Y = build_cnn_model()
        print(X.shape, Y.shape)
        load_model(sess)

        input, labels = load_data()
        # print(input.shape, labels.shape)
        # accuracy_rates = check_accuracy(X, Y, input, labels, sess)
        # print(accuracy_rates)

        ## print variable and operation names
        all_variables = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
        for variable in all_variables:
            print(variable.name)

        print("------------------------------------------------------------")
        all_ops = tf.get_default_graph().get_operations()
        for op in all_ops:
            print(op.name)


        graph = tf.get_default_graph()
        # Relu1_op = graph.get_operation_by_name('layer1/Relu')
        # Relu1 = sess.run(Relu1_op.values(), feed_dict={X: input})
        # W1 = graph.get_tensor_by_name("W1:0")
        # deconv = non_linear_deconv(np.array(Relu1), W1)
        #
        # result = sess.run(deconv)
        # print(result)


        pooling_layer_op = graph.get_operation_by_name('layer1/maxpool')
        pooling_layer, switches = sess.run(pooling_layer_op.values(), feed_dict={X: input[0:2, :, :, :]})
        print("orig swith shape", switches.shape)
        print("pooling layer shape", pooling_layer.shape)
        print(pooling_layer)
        unpooled = unpool(tf.convert_to_tensor(input[0:2, :, :, :]), pooling_layer, switches)

        print(unpooled.shape)

        W1 = graph.get_tensor_by_name("W1:0")
        deconv = non_linear_deconv(unpooled, W1)


if __name__ == '__main__':
    tf.app.run()