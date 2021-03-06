from argparse import ArgumentParser

import numpy as np
import pytorch_lightning as pl

from mvae.data import ToyDataModule
from mvae.models import PoseMVAEFactory
from mvae.utils import TensorBoardLogger, load_hparams_from_yaml

parser = ArgumentParser(description="Run Pose MVAE model")
parser.add_argument("--config", type=str, default="./configs/model.yaml")
parser.add_argument("--dataset", type=str, default="./datasets/")
parser.add_argument("--seed", type=int, default=None)

parser = pl.Trainer.add_argparse_args(parser)
arguments = parser.parse_args()

logger = TensorBoardLogger("lightning_logs")

# Seed
deterministic = False
seed = 0
if arguments.seed is not None:
    pl.seed_everything(arguments.seed)
    deterministic = True
    seed = arguments.seed

# Make trainer
trainer = pl.Trainer.from_argparse_args(arguments, logger=logger, deterministic=deterministic)

# Make data module
data_model = ToyDataModule(arguments.dataset, rotation_augmentation=False, seed=seed)

# Load parameters
params = load_hparams_from_yaml(arguments.config)
print("Load model from params \n" + str(params))

# Make model
model = PoseMVAEFactory().make_model(params)
data = np.load(arguments.dataset, allow_pickle=True)["arr_0"]
centers = data.item()["point_centers"]
colors = data.item()["point_colors"]
if "map_size" in data.item().keys():
    map_size = data.item()["map_size"]
else:
    map_size = (4, 4)
model.set_points_information(centers, colors, ((0, map_size[0]), (0, map_size[1])), 3.2, 0.1, 0.6)

print("Start training")
trainer.fit(model, data_model)
