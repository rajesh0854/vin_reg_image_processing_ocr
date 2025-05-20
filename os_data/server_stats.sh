echo""
export CODE_DIR=/datadisk/CODE_MAIN/os_data/
cd $CODE_DIR

http_srv_process_cmd=$(pgrep -af python | grep -o http.server | tail -1)
flaskapi_srv_process_cmd=$(pgrep -af python | grep -o flask_server:app | tail -1)

function oneone()
{
if [ -z "$http_srv_process_cmd" ]
then
	echo "Down"
else
	echo "Running"
fi
}

function twotwo()
{
if [ -z "$flaskapi_srv_process_cmd" ]
then
	echo "Down"
else
	echo "Running"
fi
}

http_fn=$(oneone)
flask_fn=$(twotwo)

#echo "flask_status:$flask_fn"
#echo "http status:$http_fn"
/datadisk/miniconda3/envs/trans/bin/python server_stats.py $flask_fn $http_fn
exit
