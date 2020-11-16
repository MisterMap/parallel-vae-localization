import torch.nn as nn
import torch


class PoseVaeDecoder(nn.Module):
    def __init__(self, latent_space_size, hidden_dimensions, constant_logvar=False):
        super().__init__()
        self._translation_linear = nn.Linear(hidden_dimensions[0], 2)
        self._translation_logvar_linear = nn.Linear(hidden_dimensions[0], 2)
        self._rotation_linear = nn.Linear(hidden_dimensions[0], 2)
        self._rotation_logvar_linear = nn.Linear(hidden_dimensions[0], 2)
        self._decoder = nn.Sequential(*self.make_modules(latent_space_size, hidden_dimensions))
        self._translation_logvar = None
        self._rotation_logvar = None
        if constant_logvar:
            self._translation_logvar = nn.Parameter(torch.zeros(2))
            self._rotation_logvar = nn.Parameter(torch.zeros(2))

    @staticmethod
    def make_modules(latent_space_size, hidden_dimensions):
        previous_dim = latent_space_size
        modules = []
        for dim in reversed(hidden_dimensions):
            modules.append(nn.Linear(previous_dim, dim))
            modules.append(nn.BatchNorm1d(dim))
            modules.append(nn.LeakyReLU())
            previous_dim = dim
        return modules

    def forward(self, x):
        x = self._decoder(x)
        translation = self._translation_linear(x)
        rotation = self._rotation_linear(x)
        if self._translation_logvar is None:
            translation_logvar = self._translation_logvar_linear(x)
            rotation_logvar = self._rotation_logvar_linear(x)
        else:
            translation_logvar = self._translation_logvar
            rotation_logvar = self._rotation_logvar
        return translation, rotation, translation_logvar, rotation_logvar

