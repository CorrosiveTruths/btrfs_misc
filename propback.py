#!/usr/bin/python
import argparse
import os
import sys
import filecmp
import subprocess

parser = argparse.ArgumentParser(
    description='Propagate same files with extent changes through alternative set of snapshots')
# group = parser.add_mutually_exclusive_group()
# group.add_argument("-a", "--actual", help = 'actually propagate the files through', action='store_true')
# group.add_argument("-x", "--experimental", help = 'propagate and also set received uuids to replace original snapshots (DANGEROUS)', action='store_true')
parser.add_argument('snaps', nargs='*',
                    help='snapshots to run through in order')
parser.add_argument(
    "-a", "--actual", help='create alternative snapshot timeline.propback', action='store_true')
# parser.add_argument('-d', '--debug', help = 'debug mode', action='store_true')
# Default
# parser.add_argument('-n', '--dry-run', help = "don't actually make the changes", action='store_true')
args = parser.parse_args()


def p_size(s):
    # return str(s)
    if s < 1024:
        return str(s)+'B'
    elif s < 1048576:
        return str("%.2f" % round(s/1024, 2))+'KiB'
    elif s < 1073741824:
        return str("%.2f" % round(s/1048576, 2))+'MiB'
    elif s < 1099511627776:
        return str("%.2f" % round(s/1073741824, 2))+'GiB'
    return str("%.2f" % round(s/1099511627776, 2))+'TiB'


paths = args.snaps

if len(paths) > 1:
    all_hit = 0
    all_hit_sz = 0
    firstrun = True
    ignored = []
    delete_snaps = []
    for i in range(0, len(paths)-1):
        matches = []
        sentfiles = []
        parent = os.path.normpath(paths[i])
        child = os.path.normpath(paths[i+1])
        if args.actual:
            if i == 0:
                subprocess.run(['btrfs', 'sub', 'snap', '-r',
                               parent, parent+'.propback'])
            print('Send', i+1, '/', len(paths)-1, str(parent+'.propback').replace(os.path.commonpath(
                paths), '', 1)[1:], '<>', str(child).replace(os.path.commonpath(paths), '', 1)[1:])
            p1 = subprocess.Popen(['btrfs', 'send', '--proto', '0', '--no-data', '-p',
                                  parent+'.propback', child], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        else:
            print('Send', i+1, '/', len(paths)-1, str(parent).replace(os.path.commonpath(paths),
                  '', 1)[1:], '<>', str(child).replace(os.path.commonpath(paths), '', 1)[1:])
            p1 = subprocess.Popen(['btrfs', 'send', '--proto', '0', '--no-data', '-p',
                                  parent, child], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        p3 = subprocess.Popen(['btrfs', 'rec', '--dump'],
                              stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
        p1.stdout.close()
        metadata = p3.communicate()[0].splitlines()
        if p3.returncode != 0:
            sys.exit('Receive failed: '+str(p3.returncode))

        # print(len(metadata), 'lines')

        for line in metadata:
            splitline = line.split(maxsplit=1)
            match splitline[0]:
                case 'snapshot':
                    s_path = splitline[1].split(
                        sep=' uuid=', maxsplit=1)[0].strip()
                case 'update_extent':
                    x_path = splitline[1].split(sep=' offset=', maxsplit=1)
                    x_len = x_path[1].split(sep=' len=', maxsplit=1)[1]
                    if len(sentfiles) > 0 and sentfiles[-1][1] == x_path[0].rstrip():
                        if len(sentfiles[-1]) == 3:
                            sentfiles[-1] = ((sentfiles[-1][0], sentfiles[-1]
                                             [1], int(x_len)+sentfiles[-1][2]))
                        else:
                            sentfiles[-1] = ((sentfiles[-1][0],
                                             sentfiles[-1][1], int(x_len)))
                    else:
                        # Ugh
                        sentfiles.append((splitline[0], x_path[0].rstrip().replace('\\ ', '\\\\ ').encode(
                            'latin-1').decode('unicode-escape').encode('latin-1').decode('utf-8').replace('\\ ', ' '), int(x_len)))
                    # total += int(x_len)
        # for line in sentfiles: print(*line)

        if len(sentfiles) > 0:
            print('Comparing', len(sentfiles), 'file(s)')
        hit = 0
        miss = 0
        hit_sz = 0
        miss_sz = 0
        for line in set(sentfiles): # Cludge to kill dupes, figure out where those are coming from
            if args.actual:
                left = parent+'.propback' + \
                    os.path.normpath(line[1].replace(s_path, '', 1))
            else:
                left = parent+os.path.normpath(line[1].replace(s_path, '', 1))
            right = child+os.path.normpath(line[1].replace(s_path, '', 1))
            if os.path.exists(left) == False and os.path.exists(right) == False:
                ignored.append(right.replace(
                    os.path.commonpath([left, right]), '', 1)[1:])
            elif os.path.exists(left) == False:
                miss += 1
                miss_sz += line[2]
            elif filecmp.cmp(left, right, shallow=True):  # Make tunable?
                hit += 1
                hit_sz += line[2]
                all_hit += 1
                all_hit_sz += line[2]
                matches.append(os.path.normpath(
                    line[1].replace(s_path, '', 1)))
            else:
                miss += 1
                miss_sz += line[2]
        if hit > 0:
            if args.actual:
                subprocess.run(
                    ['btrfs', 'sub', 'snap', child, child+'.propback.rw'])
                for line in matches:
                    command = ['cp', '-v', '--reflink=always', parent +
                               '.propback'+line, child+'.propback.rw'+line]
                    subprocess.run(command)
                    command = ['cp', '-v', '--preserve=all',
                               '--attributes-only', child+line, child+'.propback.rw'+line]
                    subprocess.run(command)
                subprocess.run(['btrfs', 'sub', 'snap', '-r',
                               child+'.propback.rw', child+'.propback'])
                delete_snaps.append(child+'.propback.rw')
                print('Match', hit)
            else:
                print('Match', hit, '('+p_size(hit_sz)+')')
        elif args.actual:
            subprocess.run(['btrfs', 'sub', 'snap', '-r',
                           child, child+'.propback'])
    # if len(ignored) > 0:
        # for line in ignored:
            # print('Ignored', line)
    if args.actual:
        for line in delete_snaps:
            subprocess.run(['btrfs', 'sub', 'del', line])
    else:
        print('Total matched', all_hit, '('+p_size(all_hit_sz)+')')
