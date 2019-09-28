#!/usr/bin/python3
import requests
import json
import subprocess
import os
import time
import datetime
appnames = []
app_found= []
stagelink="http://marathon-stage.net:8080/v2/apps/"
prodlinkdcos="http://mesosui-prod.net/v2/apps"
host = []
host_name = []
containerid = []
ports = []
now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
#print (now)
slave_list = []
con_list = []
##################################################################################################
# CREATE FOLDER AND MOVE THE DUMPS TO FOLDER
def file_move(file_name):
    if os.path.exists(os.path.join(os.getcwd(), containerid)):
        os.system("mv %s %s" % (file_name, containerid))
    else:
        os.system("mkdir %s" % containerid)
        os.system("mv %s %s" % (file_name, containerid))
##################################################################################################
#   FUNCTION TO GENERATE THREAD DUMP
def threadDump(java_locpass,javaid):
    print ("\nGenerating the thread log dump \n")
    thread_cmd = 'sudo su root -c "docker exec -t %s %sjcmd %s Thread.print "' % (containerid, java_locpass, javaid)
    #print (thread_cmd)
    thread_ser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, thread_cmd],
             shell=False,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE, universal_newlines=True)
    thread_out = thread_ser.communicate()[0]
    threadfile = "thread.log-%s" % now
    with open(threadfile, "w") as thread_file:
         thread_file.write ("%s" % thread_out)
    file_move(threadfile)
    print ("\nThread dump successfully generated and copied to your homedir under the folder %s with filename %s" % (containerid, threadfile))
##################################################################################################
#   FUNCTION TO GENERATE HEAP DUMP
def heapDump(java_locpass,javaid):
    print ("\n \n Generating the heap dump \n")
    heap_cmd = 'sudo su root -c "docker exec -t %s %sjmap -dump:format=b,file=/heap-%s.bin %s"' % (containerid, java_locpass, now, javaid)
    #print (heap_cmd)
    heap_ser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, heap_cmd],
             shell=False,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE, universal_newlines=True)
    heap_out = heap_ser.communicate()[0]
    #print (heap_out)
    print ("\nCopying the heap dump to jump\n")
    copy_cmd = 'sudo su root -c "docker cp %s:/heap-%s.bin . ; chmod 755 heap-%s.bin"' % (containerid, now, now)
    copy_ser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, copy_cmd],
             shell=False,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE, universal_newlines=True)
    time.sleep(220)
    heap_file="heap-%s.bin" % now
    os.system("rsync -avzP %s:~/heap-%s.bin ." % (host_name, now))
    file_move(heap_file)
    print ("\n\nHeap dump generated and copied to your homedir under the folder %s with filename %s" % (containerid, heap_file))
###################################################################################################
# SELECT ENVIRONMENT DETAILS
def linkf():
    while True:
        try:
          print ("Enter were you are in : \n\t 1. Prod dcos \n\t 2. Prod mesos \n\t 3. Stage\n")
          linkopt=int(input())
        except ValueError:
          print ("\nSorry, I didn't understand that.\n")
          continue
        if linkopt == 1 or linkopt == 2 or linkopt == 3:
          #print("\nSorry value should be 1 or 2 or 3\n")
          break
        else:
            print("\nSorry value should be 1 or 2 or 3\n")
            continue
    if linkopt is 1:
          return prodlinkdcos
    elif linkopt is 2:
        return prodlinkmesos
    else:
        return stagelink
link=linkf()
##################################################################################################
#  ENTER APPLICATION DETAILS
def applist():
        print ("Enter the application name \n")
        appse=input()
        app_req = requests.get(link, timeout=5)
        app_data = app_req.json()
        for app_list in app_data['apps']:
                appnames.append(app_list['id'])
        for app_li in appnames:
                if appse in app_li:
                        app_found.append(app_li)
        print ("\n I am able to found the following %s: \n" % appse)
        print (*app_found,sep='\n')
        print ("\n Please enter our application id:\n")
        appname=input()
        return appname
app=applist()
#####################################################################################################
#    MARATHON API TO GET THE HOST DETAILS
try:
  print ("\nGetting the application host details from the marathon api\n")
  host_req = requests.get(link + app + '/tasks', timeout=5)
  data = host_req.json()
  for task in data['tasks']:
        host_ex = task['host']
        ports_ex = task['ports']
        host.append(host_ex)
        ports.append(ports_ex[0])
  for i in (host,ports):
        print (i,end=" ")
except requests.ConnectionError:
    print("\nFailed to connect \n")
except requests.exceptions.Timeout:
    print("\nTimeout connecting to the marathon\n")
except Exception:
    print("\nError in fetching container details\n")
    exit()
#####################################################################################################
#    GETTING THE CONTAINER DETAILS FROM ALL HOSTS WHERE APP IS RUNNING
print ("\n\nGetting the container list from all the hosts\n")
for i, j in zip(host,ports):
    print ("Container in host: \t %s" % i)
    cmd = 'sudo su root -c "docker ps -a | grep "%s" | cut -c 1-12 "' % j
    logser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % i, cmd],
             shell=False,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE, universal_newlines=True)
    dockerlist = logser.communicate()[0].split("\n")
    tem=None
    tem=dockerlist[0]
    if dockerlist == []:
        error = logser.stderr.readlines()
        print >>sys.stderr, "ERROR: %s" % error
    else:
        print (*dockerlist,sep='\t')
        slave_list.append(i)
        con_list.append(tem)
#####################################################################################################
#      INPUT THE HOST AND CONTAINER DETAILS TO GET DUMP
#print (slave_list)
#print (con_list)
print ("\n\nYou need to enter the corresponding container id to generate the dump")
print ("\nEnter the corresponding container ID\n")
containerid =str(input())
print ("\n Find the corresponding host\n")
pos_con = int()
for cn in con_list:
    #print (cn)
    if cn == containerid:
       print ("Found")
       pos_con=int(con_list.index(cn))
       break
    else:
       continue
#print (pos_con)
host_name = slave_list[pos_con]
print ("\nHost:\t %s\nContainerid:\t %s" % (host_name, containerid))
#####################################################################################################
#      FINDING THE JAVA PATH FROM CONTAINER
print ("\n\nLogging to the host and finding the java installed location\n")
try:
   java_cmd = 'sudo su root -c "docker exec -t %s readlink -f /usr/bin/java"' % containerid
   java_ser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, java_cmd],
             shell=False,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE, universal_newlines=True)
   java_out = java_ser.communicate()[0].split("\n")
   javaloc = java_out[0]
   print(javaloc)
except:
   print ("Error in finding the java location\n")
#####################################################################################################
#     FINDING THE JAVA PROCESS ID and the location
print ("\nFinding the java process id\n")
try:
   java_id = 'sudo su root -c "docker exec -t %s pidof java"' % containerid
   javaid_ser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, java_id],
             shell=False,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE, universal_newlines=True)
   javaid_out = javaid_ser.communicate()[0].split("\n")
   javaid = javaid_out[0]
   print (javaid)
except:
   print ("Java process id not found\n")
if javaloc == "/opt/jdk/jdk1.8.0_151/bin/java":
  java_locpass = "/opt/jdk/jdk1.8.0_151/bin/"
  #dump(java_locpass,javaid)
elif javaloc == "/usr/lib/jvm/java-8-oracle/jre/bin/java":
  java_locpass = "/usr/lib/jvm/java-8-oracle/bin/"
  #dump(java_locpass,javaid)
else:
  print ("Java loaction not found")
#####################################################################################################
#      SWITCH CASES
while True:
   try:
      print("\nPlease select one of the following options\n")
      print("1. Take Heap dump only\n2. Take thread dump only\n3. Take heap dump and thread dump\n")
      option=int(input())
   except ValueError:
      print ("\nSorry, I didn't understand that.\n")
      continue
   if option == 1 or option == 2 or option == 3:
      break
   else:
      print("\nSorry value should be 1 or 2 or 3\n")
      continue
if option is 1:
  heapDump(java_locpass,javaid)
elif option is 2:
  threadDump(java_locpass,javaid)
else:
  threadDump(java_locpass,javaid)
  heapDump(java_locpass,javaid)
#####################################################################################################
#  REMOVE HEAP DUMP FROM SLAVE AND CONTAINER
def rem():
   try:
       rm_concmd = 'sudo su root -c "docker exec -t %s rm -rf heap-%s.bin "' % (containerid, now)
       rm_conser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, rm_concmd],
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, universal_newlines=True)
   except:
       print ("\n I am facing issue in removing file from container, please do manually\n")
   try:
       rm_sercmd = 'sudo su root -c "rm -rf heap-%s.bin"' % now
       rm_serser = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "%s" % host_name, rm_sercmd],
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, universal_newlines=True)
   except:
       print ("\n I am facing issue in removing file from slave, please do manually\n")
#####################################################################################################
# COPYING TO S3 BUCKET
print ("\n Moving the generated dump to S3 bucket under the folder with todays date \n")
try:
   os.system("AWS_ACCESS_KEY_ID=xxxxxxxxxxx AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxx aws --region=ap-southeast-1 s3 cp %s s3://xxxxxxxxxx/%s-%s/ --recursive" % (containerid, containerid, now))
   #time.sleep(220)
   os.system("rm -rf %s" % containerid)
   print ("\nRemoving files from container and slaves\n")
   rem()
   print ("\n\nDirectory %s successfully moved to the s3 bucket 'testdumper' . You can find the dir in location s3://xxxxxxxx/%s \n" % (containerid, containerid))
   print ("Please update following details to dev to download the file using the 'dumpuser' credentials \n ACCESS KEY: xxxxxxxxxxxxx \n SECRET KEY: xxxxxxxxxxxxxxxxxxxxxxxxxxx \n They can use any s3 clients to download the file just like FTP\n")
except:
   print ("Error copying folder to s3 bucket\n")
###################################################################################################
