import sys
import matplotlib.pyplot as plt
sys.path.append('/workspace')
import glio

img_path = "/workspace/dockerData"
snapshot_path = '/workspace/run_test/snapshot_000'
s = glio.GadgetSnapshot(snapshot_path)
s.load()

print("Number of particles by type:", s.header.npart)

plt.figure(figsize=(8, 8))
plt.plot(s.pos[0].T[0], s.pos[0].T[1], '.', markersize=0.1)
plt.axis('equal')
plt.grid(False)
plt.savefig(img_path+"/test_graph_gas.png", dpi=300)
plt.close()

plt.figure(figsize=(8, 8))
plt.plot(s.pos[1].T[0], s.pos[1].T[1], '.', markersize=0.1)
plt.axis('equal')
plt.grid(False)
plt.savefig(img_path+"/test_graph_dm.png", dpi=300)
plt.close()

