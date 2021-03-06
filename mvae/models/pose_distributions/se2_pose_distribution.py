from .pose_distribution import PoseDistribution
import torch
from liegroups.torch import SE2
import math


class Se2PoseDistribution(PoseDistribution):
    @property
    def mean_dimension(self):
        return 4

    @property
    def logvar_dimension(self):
        return 6

    def log_prob(self, value, mean, logvar):
        if logvar.dim() < 2:
            logvar = logvar[None].expand(mean.shape[0], logvar.shape[0])
        value_matrix = self.make_matrix(value[0], torch.nn.functional.normalize(value[1]))
        rotation = torch.nn.functional.normalize(mean[:, 2:4])
        mean_matrix = self.make_matrix(mean[:, 0:2], rotation).expand_as(
            value_matrix)
        delta_matrix = torch.bmm(self.pose_matrix_inverse(mean_matrix), value_matrix)
        delta_log = SE2.log(SE2.from_matrix(delta_matrix, normalize=False))
        if delta_log.dim() < 2:
            delta_log = delta_log[None]
        inverse_sigma_matrix = self.get_inverse_sigma_matrix(logvar).expand(delta_log.shape[0], delta_log.shape[1],
                                                                            delta_log.shape[1])
        delta_log = torch.bmm(inverse_sigma_matrix, delta_log[:, :, None])[:, :, 0]
        log_determinant = self.get_logvar_determinant(logvar)

        log_prob = torch.sum(delta_log ** 2 / 2., dim=1) + 0.5 * log_determinant + 3 * math.log(math.sqrt(2 * math.pi))
        return log_prob

    def sample(self, mean, logvar):
        mean_matrix = self.make_matrix(mean[:, 0:2], torch.nn.functional.normalize(mean[:, 2:4]))
        if logvar.dim() < 2:
            logvar = logvar[None].expand(mean.shape[0], logvar.shape[0])
        sigma_matrix = self.get_sigma_matrix(logvar)
        epsilon = torch.randn(mean.shape[0], 3, device=mean.device)
        delta = torch.bmm(sigma_matrix, epsilon[:, :, None])[:, :, 0]
        delta_matrix = SE2.exp(delta).as_matrix()
        if delta_matrix.dim() < 3:
            delta_matrix = delta_matrix[None]
        position_matrix = torch.bmm(mean_matrix, delta_matrix)
        positions = torch.zeros(mean.shape[0], 3)
        positions[:, 0] = position_matrix[:, 0, 2]
        positions[:, 1] = position_matrix[:, 1, 2]
        positions[:, 2] = torch.atan2(position_matrix[:, 1, 0], position_matrix[:, 0, 0])
        positions = positions.cpu().detach().numpy()
        return positions

    @staticmethod
    def make_matrix(translation, rotation):
        rotation = torch.nn.functional.normalize(rotation)
        matrix = torch.zeros(rotation.shape[0], 3, 3, device=translation.device)
        matrix[:, 2, 2] = 1
        matrix[:, 0, 0] = rotation[:, 0]
        matrix[:, 0, 1] = -rotation[:, 1]
        matrix[:, 1, 1] = rotation[:, 0]
        matrix[:, 1, 0] = rotation[:, 1]
        matrix[:, 0, 2] = translation[:, 0]
        matrix[:, 1, 2] = translation[:, 1]
        return matrix

    @staticmethod
    def pose_matrix_inverse(matrix):
        result = torch.zeros_like(matrix)
        rotation_part = matrix[:, :2, :2]
        translation_part = matrix[:, :2, 2]
        rotation_part_transposed = torch.transpose(rotation_part, 1, 2)
        result[:, :2, :2] = rotation_part_transposed
        result[:, :2, 2] = -torch.bmm(rotation_part_transposed, translation_part[:, :, None])[:, :, 0]
        result[:, 2, 2] = 1
        return result

    @staticmethod
    def get_sigma_matrix(logvar):
        matrix = torch.zeros(logvar.shape[0], 3, 3, device=logvar.device)
        matrix[:, 0, 0] = torch.exp(0.5 * logvar[:, 0])
        matrix[:, 1, 1] = torch.exp(0.5 * logvar[:, 1])
        matrix[:, 2, 2] = torch.exp(0.5 * logvar[:, 2])
        matrix[:, 1, 0] = torch.exp(0.25 * logvar[:, 1] + 0.25 * logvar[:, 0]) * torch.sinh(logvar[:, 3])
        matrix[:, 2, 1] = torch.exp(0.25 * logvar[:, 1] + 0.25 * logvar[:, 2]) * torch.sinh(logvar[:, 4])
        matrix[:, 2, 0] = torch.exp(0.25 * logvar[:, 2] + 0.25 * logvar[:, 0]) * torch.sinh(logvar[:, 5])
        matrix = matrix.permute(0, 2, 1)
        return matrix

    @staticmethod
    def get_logvar_determinant(logvar):
        return logvar[:, 0] + logvar[:, 1] + logvar[:, 2]

    @staticmethod
    def get_inverse_sigma_matrix(logvar):
        matrix = torch.zeros(logvar.shape[0], 3, 3, device=logvar.device)
        a1 = torch.exp(-0.5 * logvar[:, 0])
        d1 = torch.exp(-0.5 * logvar[:, 1])
        f1 = torch.exp(-0.5 * logvar[:, 2])
        b = torch.exp(0.25 * logvar[:, 1] + 0.25 * logvar[:, 0]) * torch.sinh(logvar[:, 3])
        e = torch.exp(0.25 * logvar[:, 1] + 0.25 * logvar[:, 2]) * torch.sinh(logvar[:, 4])
        c = torch.exp(0.25 * logvar[:, 0] + 0.25 * logvar[:, 2]) * torch.sinh(logvar[:, 5])
        b1 = - b * a1 * d1
        e1 = - e * d1 * f1
        c1 = - c * a1 * f1 - e * b1 * f1
        matrix[:, 0, 0] = a1
        matrix[:, 1, 1] = d1
        matrix[:, 2, 2] = f1
        matrix[:, 1, 0] = b1
        matrix[:, 2, 1] = e1
        matrix[:, 2, 0] = c1
        matrix = matrix.permute(0, 2, 1)
        return matrix

    def mean_position(self, mean, logvar):
        return mean[:, 0:2]
