import h5py, numpy as np, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
shutil.copy(src, dst)
with h5py.File(dst, "r+") as f:
    f.copy("PartType1", "PartType3")
    del f["PartType1"]
    for key in ["NumPart_ThisFile", "NumPart_Total"]:
        arr = np.array(f["Header"].attrs[key])
        arr[3] = arr[1]; arr[1] = 0
        f["Header"].attrs[key] = arr
    print(f"Done: {f['PartType3/Coordinates'].shape[0]} particles")
