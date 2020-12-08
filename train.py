from argparse import ArgumentParser
from torch.utils.data import DataLoader, SubsetRandomSampler
from torchvision.datasets import ImageFolder
import os
import pandas as pd
import torch
import sklearn.metrics as metrics
from sklearn.model_selection import StratifiedKFold
import numpy as np
# Local imports
from arguments import get_parser
from models import Classifier 
from dataloader import get_dataloader

def make_message(loss, accuracy, epoch, is_best):
    msg = "Validation results, EPOCH {} : Loss {} | Accuracy {}".format(epoch, loss, accuracy)
    if is_best:
        msg = msg.upper()
    return msg

def train(model, dataloader):
    model.network.train()
    for input_batch, target_batch in dataloader:
        model.counter['batches'] += 1
        loss = model.optimize_parameters(input_batch, target_batch)
        mean_loss = get_value(loss)
        if model.writer:
            model.writer.add_scalar("Training_loss_{}".format(model.name), mean_loss, model.counter['batches'])
    model.counter['epochs'] += 1

def val(model, dataloader):
    model.network.eval()
    accuracy = []
    loss = []
    for input_batch, target_batch in dataloader:
        target_batch = target_batch.to(model.device, dtype=torch.int64)
        output, pred = model.predict(input_batch)
        loss.append(model.criterion(output, target_batch).detach().cpu().numpy())
        y_pred += pred
        y_true += target_batch.cpu().numpy()
    accuracy = metrics.accuracy_score(y_true, y_pred)
    loss = np.mean(loss)
    state = model.make_state()
    if model.writer:
        model.writer.add_scalar("Validation_loss_{}".format(model.name), loss, model.counter['batches'])
        model.writer.add_scalar("Validation_acc_{}".format(model.name), accuracy, model.counter['batches'])
    is_best = model.early_stopping(accuracy, state, model.name, minim=False)
    print(make_message(loss, accuracy, model.counter['epochs'], is_best))
    
def get_value(tensor):
    return tensor.detach().cpu().numpy()

def main():
    args = get_parser().parse_args()

    # Make datasets
    train_dir = os.path.join(args.train_dir,'train')
    val_dir = os.path.join(args.val_dir, 'val')
    train_loader = get_dataloader(train_dir, args.batch_size, args.pretrained, args.augmented)
    val_loader = get_dataloader(val_dir, args.batch_size, args.pretrained, False)

    args.num_class = len(train_loader.dataset.classes)
    args.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
 
    ## Initialisation model
    model = Classifier(args=args)

    while model.counter['epochs'] < args.epochs:
        print("Begin training")
        train(model=model, dataloader=train_loader)
        val(model=model, dataloader=val_loader)
        if model.early_stopping.early_stop:
            break
    if model.writer:
        model.writer.close()

if __name__ == "__main__":
    main()