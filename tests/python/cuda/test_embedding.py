import os

import torch
from torch import device, nn
from torch.nn.parallel import DistributedDataParallel
import torch.distributed as dist
import torch.multiprocessing as mp

import torch_quiver as torch_qv
from quiver import Embedding


device_list = [0, 1]
n_embedding = 4
d_embedding = 16
batch_size = 8


class Model(nn.Module):
  def __init__(self, n_emb, d_emb, rank, device_list) -> None:
    super().__init__()
    self.emb = Embedding(n_emb, d_emb, rank, device_list)
    self.mlp = nn.Linear(d_emb, 1)

  def forward(self, idx):
    embs = self.emb(idx)
    y = self.mlp(embs)
    return y


def simple_test():
  """
  Test basic embedding lookup
  """
  rank = 1
  device = torch.device('cuda', rank) if torch.cuda.is_available() else 'cpu'
  model = Model(n_embedding, d_embedding, rank, device_list).to(device)
  with torch.no_grad():
    x = torch.randint(0, n_embedding, (batch_size,), dtype=torch.long)
    y_ = model(x)
    print(y_)


def mp_test_emb(rank: int, embedding):
  x = torch.randint(0, n_embedding, (batch_size,), dtype=torch.long)
  # print(rank, embedding(x))
  print(rank, embedding.rank, embedding.n_embeddings)


def mp_test(rank: int, world_size: int):
  """
  Test embedding lookup with multiprocess
  """
  dist.init_process_group(backend='nccl', world_size=world_size, rank=rank)

  device = torch.device('cuda', rank) if torch.cuda.is_available() else 'cpu'

  model = Model(n_embedding, d_embedding, rank, device_list).to(device)
  model = DistributedDataParallel(model, device_ids=[rank])

  with torch.no_grad():
    x = torch.randint(0, n_embedding, (batch_size,), dtype=torch.long)
    y_ = model(x)
    print(y_)

  dist.destroy_process_group()


if __name__ == '__main__':
  torch_qv.init_p2p(device_list)

  os.environ['MASTER_ADDR'] = 'localhost'
  os.environ['MASTER_PORT'] = '39871'

  n_devices = len(device_list)
  # simple_test()
  # mp.spawn(mp_test, (n_devices,), n_devices)
  embedding = Embedding(n_embedding, d_embedding, 0, device_list)
  mp.spawn(mp_test_emb, (embedding,), n_devices)
