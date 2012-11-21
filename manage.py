#! /usr/bin/python
# Ian Dimayuga's EC2 Management

import sys
import time
import argparse
import json
import boto
import boto.ec2
from os import path

config_json = path.join(path.dirname(__file__), 'config.json')
config = json.loads( open(config_json, "r").read())
if not config or not "addresses" in config or not "instances" in config or not "regions" in config or not "sizes" in config:
  print "Failed to load config.json."
  sys.exit(-1)
parser = argparse.ArgumentParser()
verbose = False
sleepTime = 2

# main method
def main():
  instanceNames = [json.dumps(key).replace('\"','') for key in config["instances"].keys()]
  sizeNames = [json.dumps(key).replace('\"','') for key in config["sizes"].keys()]
  addressNames = [json.dumps(key).replace('\"','') for key in config["addresses"].keys()]

  # get options
  parser.add_argument("instance", help="Name of instance.", choices=instanceNames)
  parser.add_argument("-s", "--status", help="Display data about the instance.", action="store_true")
  parser.add_argument("-u", "--start", help="Start or restart instance", action="store_true")
  parser.add_argument("-d", "--stop", help="Stop instance. If --start is flagged, this will start and then stop the instance.", action="store_true")
  parser.add_argument("-r", "--resize", help="Change size of instance. If the instance is running it will be restarted. Nothing happens if instance is already this size.", choices=sizeNames)
  parser.add_argument("-i", "--address", help="Assign an IP address to the instance. Note that this does nothing if --stop.", choices=addressNames)
  parser.add_argument("-v", "--verbose", help="Display verbose output. This will also pretty-print --status.", action="store_true")
  args = parser.parse_args()

  # set flags
  global verbose
  verbose = args.verbose
  status = args.verbose or args.status

  # find the region name
  region = config["regions"][args.instance]

  # connect to EC2
  conn = boto.ec2.connect_to_region(region)
  if not conn:
    print "Failed to connect to EC2 region {r}.".format(r=region)
    sys.exit(-1)

  # get Instance object
  instanceID = config["instances"][args.instance]
  instance = conn.get_all_instances(filters={'instance-id':instanceID})[0].instances[0]
  if not instance:
    print "Failed to retrieve the specified instance '{i}' (id: {id}).".format(i=args.instance, id=instanceID)
    sys.exit(-1)

  hasRestarted = False
  # Resizing may already restart the instance
  if args.resize:
    print "***Resize instance '{name}' to {size}***".format(name=args.instance, size=config["sizes"][args.resize])
    hasRestarted = resize(instance, args.resize)

  if args.start and not hasRestarted:
    if instance.state == "running":
      print "***Reboot instance '{name}'***".format(name=args.instance)
      printv("Rebooting instance...")
      instance.reboot()
      time.sleep(sleepTime)
    else:
      print "***Start instance '{name}'***".format(name=args.instance)
      printv("Starting instance...")
      instance.start()
    while instance.state != "running":
      time.sleep(sleepTime)
      instance.update()
    printv("Instance is running.")

  if args.stop:
    print "***Stop instance '{name}'***".format(name=args.instance)
    printv("Stopping instance...")
    instance.stop()
    while instance.state != "stopped":
      time.sleep(sleepTime)
      instance.update()
    printv("Instance is stopped.")

  elif args.address:
    print "***Assign '{ip}' IP address to instance '{name}'***".format(ip=args.address, name=args.instance) 
    if instance.state != "running" and instance.state != "pending":
      print "Cannot assign an IP address to a stopped or stopping instance"
    else:
      assign(instance, args.address)
      printv("IP address is now {ip}".format(instance.ip_address))

  if status:
    display(args.instance, instance, region)

def display(name, instance, region):
  output = {}
  output['name'] = name
  output['region'] = region
  output['id'] = instance.id
  output['type'] = instance.instance_type
  output['address'] = instance.ip_address
  output['state'] = instance.state
  print json.dumps(output, indent = 4 if verbose else None)

def printv(output):
  if verbose:
    print "\t" + output

# Return value: True if the instance was restarted as a result of this function.
#               False if either the instance was already this size, or if the instance was stopped to begin with.
def resize(instance, size):
  size = config["sizes"][size]
  if instance.instance_type == size:
    printv("The instance is already size {s}.".format(s=size))
    return False
  
  running = False
  while instance.state != "stopped":
    if instance.state == "running":
      running = True
      printv("This instance is running. Stopping instance...")
      instance.stop()
    time.sleep(sleepTime)
    instance.update()
  printv("This instance is stopped.")

  printv("Resizing instance...")
  if not instance.modify_attribute("instanceType", size):
    print "Failure to modify instance-type."
    sys.exit(-1)
  
  while instance.instance_type != size:
    time.sleep(sleepTime)
    instance.update()
  printv("Instance is now %s." % size)

  if running:
    printv("Starting instance...")
    instance.start()
    while instance.state != "running":
      time.sleep(sleepTime)
      instance.update()
    printv("Instance is running.")
    return True
  return False

# Assigns an IP address to the instance
def assign(instance, address):
  address = config["addresses"][address]
  printv("Assigning IP address %s to instance..." % address)
  if not instance.use_ip(address):
    print "Failure to associate Elastic IP address."
    sys.exit(-1)
  while instance.ip_address != address:
    time.sleep(sleepTime)
    instance.update()
  printv("Successfully assigned address.")

if __name__ == "__main__":
  main()
