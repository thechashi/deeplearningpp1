import numpy as np
import torch
from pathlib import Path
from tqdm import tqdm
from models import VGG



def load_model(model_path, conf):
    """

    :param model_path: the path where model is present
    :param conf: configurator
    :return: configurator
    """
    checkpoint = torch.load(model_path)
    conf["model"].load_state_dict(checkpoint["model"])
    conf["current_epoch"] = checkpoint["epoch"]
    conf["optimizer"].load_state_dict(checkpoint["optimizer"])
    conf["scheduler"].load_state_dict(checkpoint["scheduler"])


def remove_files(*argv):
    """

    :param argv: list of files that has to be deleted
    :return:
    """
    for file in argv:
        if Path(file).is_file():
            Path(file).unlink()


def directory_creator(*argv):
    """

    :param argv: list directories to be created
    :return:
    """
    for arg in argv:
        if not Path(arg).is_dir():
            Path(arg).mkdir(parents=True)


def loader(img_path):
    """
    This function will load the images which are in npz format
    :param img_path: The path from which the images are loaded
    :return: image matrix
    """
    image = np.load(img_path)
    image = image.f.arr_0  # Load data from inside file.
    return image


def model_selection(conf):
    """
    This will load the model and return the model instance
    :param conf: Configurator
    :return:
    """

    conf["model"] = VGG(conf["in_channels"], conf["out_channels"], conf["base_channels"],
                        conf["n_conv_sections"], conf["input_shape"])
    return conf


def check_load_model(conf):
    """
    This function checks if trained model is present and load;
    :param conf:
    :return:
    """

    # setting current and best model save paths. Creating the directories if not existing
    current_model_path = Path(conf["save_model_path"]) / "current"
    best_model_path = Path(conf["save_model_path"]) / "best"
    directory_creator(conf["current_model_path"], conf["best_model_path"])

    # loading current model
    current_model_list = list(current_model_path.rglob("*.pt"))
    current_model_list = sorted(current_model_list)

    # loading best model
    best_model_list = list(best_model_path.rglob("*.pt"))
    best_model_list = sorted(best_model_list)
    if not current_model_list:
        current_model = ""
    else:
        current_model = current_model_list[-1]
    if not best_model_list:
        best_model = ""
    else:
        best_model = best_model_list[-1]

    # setting the optimizers and scheduler
    conf['optimizer'] = torch.optim.SGD(conf['model'].parameters(), lr=conf["learning_rate"], momentum=conf["momentum"])
    conf['scheduler'] = torch.optim.lr_scheduler.MultiStepLR(conf['optimizer'], [100, 200, 400], gamma=0.5)
    conf["current_model"] = current_model
    conf["best_model"] = best_model
    conf["current_epoch"] = 0

    # load if save model existing
    if current_model.exists():
        load_model(current_model, conf)
    elif best_model.exists():
        load_model(best_model, conf)

    for param_group in conf["optimizer"].param_groups:
        param_group["lr"] = conf["learning_rate"]
    return conf


def model_saving(conf, model_path):
    """
    This function will be used to save the model
    :param conf:
    :param model_path:
    :return: 
    """
    save_params = {
        "epoch": conf["step"],
        "model": conf["model"].state_dict(),
        "optimizer": conf["optimizer"].state_dict(),
        "scheduler": conf["scheduler"].state_dict(),
    }
    model_path = Path(model_path)
    model_folder = model_path.parent
    directory_creator(model_folder)
    torch.save(save_params, model_path)


def model_training(conf):
    """
    This method contains the training code of model
    :param conf:
    :return:
    """

    train_loss = 0
    criterion = conf["criterion"]
    model = conf["model"]
    device = conf["device"]
    model.train(True)
    with torch.autograd.set_detect_anomaly(True):
        with torch.autograd.set_grad_enabled(True):
            for batch_idx, sample in enumerate(tqdm(conf["training_generator"])):
                image = sample["image"].to(device)
                target = sample["target"].to(device)

                conf["optimizer"].zero_grad()
                image_pred = model(image)
                loss = criterion(image_pred, target)

                train_loss = train_loss + (
                        (1 / (batch_idx + 1)) * (loss.data - train_loss)
                )
                loss.backward()
                conf["optimizer"].step()
            conf["scheduler"].step()

    conf["train_loss"] = train_loss
    return conf


def model_validation(conf):
    """
    this method contains the validation code for the model
    :param conf:
    :return:
    """
    valid_loss = 0
    criterion = conf["criterion"]
    model = conf["model"]
    device = conf["device"]
    model.eval()
    with torch.no_grad:
        for batch_idx, sample in enumerate(tqdm(conf["training_generator"])):
            image = sample["image"].to(device)
            target = sample["target"].to(device)
            image_pred = model(image)
            loss = criterion(image_pred, target)
            valid_loss = valid_loss + (
                    (1 / (batch_idx + 1)) * (loss.data - valid_loss)
            )
    conf["valid_loss"] = valid_loss






    
