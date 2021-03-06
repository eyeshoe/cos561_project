import argparse, time, subprocess, collections, operator, json
import pdb
import scapy.all as sc

parser = argparse.ArgumentParser()
parser.add_argument('--timeout', '-t', type=int)
parser.add_argument('--analyze', action='store_true')
# Input should be a path to a video I think
parser.add_argument('--input', '-i')
parser.add_argument('--output', '-o')
args = parser.parse_args()


class NetworkTrace:

        def __init__(self):
                self.currTime = None
                self.pkts = None
                self.data = None
                self.firstTS = None

        def sniff(self):
                print("Sniffing...")
                if args.timeout:
                        self.pkts = sc.sniff(filter="tcp", timeout=args.timeout)
                        print(str(self.pkts))
                else:
                        print("Need timeout")
                        return

                self.currTime = int(time.time())
                sc.wrpcap("data/sniff_{0}.cap".format(self.currTime), self.pkts)

        def getTS(self, pkt):
                for option in pkt[sc.TCP].options:
                        if option[0] == "Timestamp":
                                return option[1]

        def analyze(self):
                siteIPs = []
                print("Analyzing...")
                srcIPs = collections.defaultdict(int)
                for pkt in self.pkts:
                        srcIPs[pkt[sc.IP].src] += 1
                sortedIPs = sorted(srcIPs.items(), key=operator.itemgetter(1), reverse=True)
                for (ip, _) in sortedIPs:
                        print("checking out " + ip)
                        p1 = subprocess.Popen(['nslookup', ip], stdout=subprocess.PIPE)
                        p2 = subprocess.Popen(['grep', '-e', 'twitch', '-e', 'ttvnw'], stdin=p1.stdout, stdout=subprocess.PIPE)
                        o = p2.communicate()
                        if len(o[0]) > 0:
                                siteIPs.append(ip)
                sitePkts = [pkt for pkt in self.pkts if pkt[sc.IP].src in siteIPs]
                sc.wrpcap("data/analyze_{0}.cap".format(self.currTime), sitePkts)

                self.firstTS = self.getTS(sitePkts[0])[1]
                self.data = [{'len': x[sc.IP].len, 'ts': self.getTS(x)[1] - self.firstTS} for x in sitePkts]


if __name__ == "__main__":
        print("Creating network trace")
        nt = NetworkTrace()
        if args.input:
                nt.currTime = int(time.time())
                nt.pkts = sc.rdpcap(args.input)
        else:
                nt.sniff()
        if args.analyze:
                nt.analyze()
                if args.output:
                        with open(args.output, 'wb') as oFile:
                                oFile.write(json.dumps(nt.data))
                else:
                        print(str(nt.data))
        else:
                print("Done")

