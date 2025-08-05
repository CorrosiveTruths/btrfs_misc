# btrfs_misc
Miscellaneous tools for brtfs
# Propback.py
A backwards propagator takes a set of snapshots, uses incremental btrfs send / receive to identify files with extent changes between snapshots, compares the files for equality, and then propagates those versions back through an alternative set of snapshots.

In effect this de-duplicates all files that are the same, but have different extent layouts, for example, defragged files, or non-reflinked copies of files (from an installer or received full subvolume). Originally the idea was to recover space in a backup set from a reguarlarly defragged filesystem. It is fast because it doesn't compare every file, just the files wih extent changes, through a set a snapshots.

Try something like ````propback.py `find `
