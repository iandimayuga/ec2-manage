#! /usr/bin/python
# Ian Dimayuga's EC2 Management

import sys
import argparse
import json
import boto

config = json.loads( open("config.json", "r").read())
if not config:
  print "Failed to load config.json."
  sys.exit(-1)
parser = argparse.ArgumentParser()

# main method
def main():
  # get options
  parser.add_argument("instance", help="Name of instance.", choices=[json.dumps(key) for key in config["instances"].keys()])
  parser.add_argument("-u", "--start", help="Start or restart instance", action="store_true")
  parser.add_argument("-d", "--stop", help="Stop instance. If --start is flagged, this will start and then stop the instance.", action="store_true")
  parser.add_argument("-r", "--resize", help="Change size of instance. Nothing happens if instance is already this size.", choices=[json.dumps(key) for key in config["sizes"].keys()])
  parser.add_argument("-i", "--address", help="Assign an IP address to the instance. Note that a stopped instance will not retain its address.", choices=[json.dumps(key) for key in config["addresses"].keys()])
  parser.parse_args()

  # connect to EC2
  conn = boto.connect_ec2()
  if not conn:
    print "Failed to connect to EC2."
    sys.exit(-1)

  instance = conn.get_all_instances(filters={'instance-state-name':'stopped'})[0][0]
  if not instance:
    print "Failed to get the specified instance."
    sys.exit(-1)

def resize(conn, instance, size):
  
  running = (instance.state == "running")
  while instance.state != "stopped":
    if running:
      print "This instance is running. Stopping instance..."
      instance.stop()
    instance.update()




if __name__ == "__main__":
  main()
