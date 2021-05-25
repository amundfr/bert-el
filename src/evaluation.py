"""
Author: Amund Faller Råheim

Functions for:
 * Accuracy calculation:
     * over mention or
     * over candidate
 * Read output file from previous evaluation, and get accuracy
 * Plot evaluation results
"""

import numpy as np
import matplotlib.pyplot as plt
from os.path import isdir, isfile, join
from collections import Counter


def accuracy_over_mentions(preds, labels, docs, mentions, candidates=None):
    """
    Calculate the accuracy of a classification prediction
    over mentions, using the argmax of the preds.

    This is achieved by grouping by mentions, and choosing the highest
    positive prediction as the only prediction of the True label.

    :param preds: logit predictions from the model
    :param labels: the correct true/false labels for each candidate/data point
    :param docs: list of docs index for all data points
    :param mentions: list of the mention index in docs for all data points
    :param candidates: list of candidate names for all data points
        (triggers a verbose return string)

    :returns: a scalar accuracy for this batch, averaged over mentions,
        and, is 'candidates' is provided, the full results as a csv table
    """
    assert len(preds) == len(labels)
    assert len(preds) == len(docs)
    assert len(preds) == len(mentions)

    # Counts number of data points for each candidate,
    #  identified by doc ID + mention ID
    ctr = Counter(zip(docs, mentions))
    n = len(ctr)

    # Preparing to return all the results as a csv table
    result_str = ""
    if candidates and len(candidates) == len(preds):
        result_str = "doc; mention_i; mention; accuracy; " \
                     "candidate; label; top_pred; prediction\n"
    else:
        candidates = None

    # Iterate the lists mention by mention:
    tot_accuracy = 0
    i = 0
    while i < len(preds):
        # Mention identitifed by doc + mention in dataset
        mention_key = (docs[i], mentions[i])
        # Number of data points / candidates for this mention
        n_data_points = ctr[mention_key]

        # Get all predictions and labels for this mention
        mention_preds = preds[i:i + n_data_points]
        mention_labels = labels[i:i + n_data_points].flatten()
        assert len(mention_labels[mention_labels == 1.0]) <= 1

        # Pick single top prediction that BERT thinks is True as candidate
        pred_true = np.argmax(mention_preds, axis=0)[0]
        # Check if BERT actually predicts this to be True:
        if mention_preds[pred_true] > 0:  # if mention_preds[pred_true, 1] > 0:
            # One-hot vector of the top prediction
            pred = np.eye(n_data_points)[pred_true]
        # Else, NO candidates are True
        else:
            pred = np.zeros(n_data_points)
        # Accuracy for this mention
        mention_accuracy = 1.0 if np.all(np.equal(pred, mention_labels)) else 0
        tot_accuracy += mention_accuracy

        # If in verbose mode
        if candidates:
            mention_candidates = candidates[i:i + n_data_points]
            mention_gt = mention_candidates[np.argmax(mention_labels)]
            for candidate, top_pred, cand_pred, label in zip(
                    mention_candidates, pred, mention_preds, mention_labels):
                result_str += f"{docs[i] + 1:>4}; {mentions[i]:>3}; " \
                              f"{mention_gt:>12}; {mention_accuracy:>3.1f}; " \
                              f"{candidate:>12}; {label:>3.1f}; " \
                              f"{top_pred:>3.1f}; {cand_pred}\n"

        i += n_data_points

    return tot_accuracy / n, result_str


def accuracy_over_candidates(preds, labels):
    """
    Calculate the accuracy of a classification prediction
    over candidates ("naïvely"), using the argmax of the preds.

    :param preds: logit predictions from the model
    :param labels: the correct true/false labels for each data point
    :returns: a scalar accuracy for this batch, averaged over candidates
    """
    pred_classes = np.argmax(preds, axis=1).flatten()
    return np.sum(pred_classes == labels.flatten()) / len(labels)


def read_result_and_evaluate(file: str = 'data/evaluation_result.csv'):
    """
    Reads the file generated by test function when passing a docs_mentions.
    Use as a shortcut to evaluate results without reevaluating the model.

    :param file: path to the csv file containing
        the output from the test function
    """
    if not isfile(file):
        raise FileNotFoundError(f"Could not find file at {file}.")

    docs = []
    mentions = []
    logits = []
    labels = []
    with open(file) as f:
        # Skip header
        next(f)
        for line in f:
            col = line.split(';')
            if len(col) < 7:
                break
            docs.append(int(col[0]))
            mentions.append(int(col[1].strip()))
            label = float(col[5].strip())
            logit = col[7].strip()[2:-1].split(' ')
            # Convert the logits (that are not empty string) to floats
            logit = [float(lo) for lo in logit if lo]
            labels.append(label)
            logits.append(logit)

    labels = np.expand_dims(np.array(labels), -1)
    logits = np.array(logits)

    avg_accuracy, _ = accuracy_over_mentions(logits, labels, docs, mentions)
    print(f"Test accuracy: {avg_accuracy:.4f}")


def plot_training_stats(training_stats, save_to_dir: str = None):
    """
    Plot training statistics. 
    Specifically, loss over epochs and accuracy over epochs
    
    :param training_stats: data returned from ModelTrainer after training
    :param save_to_dir: if provided, the plots are saved to this destination
    """
    x_ = list(range(len(training_stats)))

    # Increase the size of the plot (set dots per inch)
    scale = 1.8
    fig_1, ax_1 = plt.subplots(dpi=scale * 72)

    tr_loss = [s['Training Loss'] for s in training_stats]
    ax_1.scatter(x_, tr_loss, s=64, marker='x')
    ax_1.plot(x_, tr_loss)

    val_loss = [s['Valid. Loss'] for s in training_stats]
    ax_1.scatter(x_, val_loss, s=64, marker='x')
    ax_1.plot(x_, val_loss)

    ax_1.grid()
    fig_1.legend(["Training loss", "Validation loss"])

    fig_2, ax_2 = plt.subplots(dpi=scale * 72)

    tr_loss = [s['Valid. Accur.'] for s in training_stats]
    ax_2.scatter(x_, tr_loss, s=64, marker='x')
    ax_2.plot(x_, tr_loss)
    ax_2.grid()

    if save_to_dir and isdir(save_to_dir):
        fig_1.savefig(join(save_to_dir, 'losses.png'))
        fig_2.savefig(join(save_to_dir, 'accuracy.png'))

    fig_1.show()
    fig_2.show()
