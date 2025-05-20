import psutil
from datetime import datetime
import mysql.connector
import logging
import os
import subprocess as sp
import sys
from settings import DBCONN
from settings import PROCESS_UTIL
import pickle
import redis
import json

logging.basicConfig(filename='logs.txt', level=logging.INFO, format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
redis_db=redis.Redis(host='10.50.0.67', port=6379, db=0)

hsrp_image_save=PROCESS_UTIL.SAVE_HSRP_IMG_DIR
vin_image_save=PROCESS_UTIL.SAVE_VIN_IMG_DIR

flask_running_status=str(sys.argv[1])
httpserver_running_status=str(sys.argv[2])

def get_stat():
  mem_usage=psutil.virtual_memory()[2]
  cpu_usage=psutil.cpu_percent()
  tothsrp_images=0
  totvin_images=0
  tot_req=0

  dict = json.loads(redis_db.get('vinreg'))
  tothsrp_images=int(dict['counthsrp'])
  totvin_images=int(dict['countvin'])
  tot_req=int(dict['requestid'])
  return mem_usage,cpu_usage,tothsrp_images,totvin_images,tot_req


def get_gpu_memory():
  gpu_mem_used = "nvidia-smi --query-gpu=memory.used --format=csv"
  memory_used_info = sp.check_output(gpu_mem_used.split()).decode('ascii').split('\n')[:-1][1:]
  memory_free_values = [int(x.split()[0]) for i, x in enumerate(memory_used_info)]
  return memory_free_values

mem_usage,cpu_usage,tothsrp_images,totvin_images,tot_req=get_stat()
gpu_mem_use=get_gpu_memory()
gpu_mem_use_f=gpu_mem_use[0]

SQL=f"""INSERT INTO vinreg_ostats (capture_date,cpu_use,mem_use,gpu_mem_use,tot_vin_images,tot_hsrp_images,tot_req,flask_srv_status,http_srv_status,server_name)
            VALUES (now(),'{cpu_usage}','{mem_usage}','{gpu_mem_use_f}','{totvin_images}','{tothsrp_images}','{tot_req}','{flask_running_status}','{httpserver_running_status}','VM1');
          """
print(SQL)
try:
  connection = mysql.connector.connect(host=DBCONN.HOST,
                                     database=DBCONN.DB,
                                     user=DBCONN.USER,
                                     password=DBCONN.PASSWORD,
                                     port=DBCONN.PORT)
except mysql.connector.Error as error:
  logging.error('database connection failed')
else:
  cursor = connection.cursor()
  cursor.execute(SQL)
  connection.commit()
  cursor.close()
  connection.close()
  logging.info('data stored successfully')


'''
create table vinreg_ostats(capture_date datetime,cpu_use varchar(10),mem_use varchar(10),gpu_mem_use varchar(10),tot_vin_images int(20),tot_hsrp_images int(20),tot_req int(20),flask_srv_status varchar(10),http_srv_status varchar(10))
pip3.6 install mysql-connector-python==3.0.29
'''

