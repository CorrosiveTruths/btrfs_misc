# btrfs_misc
Miscellaneous tools for brtfs
# Propback.py
This backwards propagator takes a set of snapshots, uses incremental btrfs send / receive to identify files with extent changes between snapshots, compares the files for equality (python filecmp, but can add other options if need be), and then propagates those versions back through an alternative set of snapshots.

In effect this de-duplicates all files that are the same, but have different extent layouts, for example, defragged files, or non-reflinked copies of files (from an installer or received full subvolume). Originally the idea was to recover space in a backup set from a regularly defragged filesystem.

Try something like:

With Snapper layout (change key column to the one with snapshot numbers)
````
propback.py `find /mnt/.snapshots/*/snapshot -maxdepth 0 | sort -t/ -k3rn`
````
Just reverse sorting with sort -r will work with other schemes that name the snapshots by date.

This will run through the snapshots and return how many files are being compared, how many matched, and how much space in extents are being updated.

Running with -a will create an alternative set of snapshots appended with .propback and propagate matching files backwards through that created set, with attributes copied from the original snapshot, not touching the original ones at all, only the copies. Running something like compsize on the original set and then the .propback set should show less disk usage & fewer extents (if files have been defragged at least).

This script is largely a proof of concept for the approach. Check the results before keeping the created snapshots or replacing the originals.
