import mysql.connector
import logging
from settings import DBCONN
from settings import PROCESS_UTIL

SQL=f"""delete from vinreg_ostats where capture_date < DATE_SUB(NOW(), INTERVAL 30 DAY); """
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
  logging.info('query execute successfully')
  logging.info(SQL)

