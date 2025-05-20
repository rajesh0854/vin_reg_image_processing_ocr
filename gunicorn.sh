function guni_stop()
{
gunicorn_pid=$(pgrep -af flask_server:app | head -1 |  awk '{print $1}')
cd $FLASK_DIR
if [ -z "$gunicorn_pid" ]
then
        echo "Warning : gunicorn is not running!."
else
        kill $gunicorn_pid
        echo >nohup.out
        echo ""
        echo "gunicorn process with pid $gunicorn_pid has been killed!"
        echo ""
fi
}

function redis_stop()
{
redis_pid=$(ps -ef | grep redis-server | grep 'hmcl_ad' | head -1 |  awk '{print $2}')
cd $REDIS_DIR
if [ -z "$redis_pid" ]
then
        echo "Warning : redis is not running!."
else
        kill $redis_pid
        echo >nohup.out
        echo ""
        echo "redis process with pid $redis_pid has been killed!"
        echo ""
fi
}

function guni_start()
{
cd $FLASK_DIR
echo >nohup.out
nohup gunicorn -w 5 -b 0.0.0.0:5001 --timeout 200 'flask_server:app' &
sleep 1
gunicorn_pid=$(pgrep -af flask_server:app | head -1 |  awk '{print $1}')
if [ -z "$gunicorn_pid" ]
then
        echo "Warning : failed to start gunicorn! check if process is already running."
else
        echo "gunicorn started with pid $gunicorn_pid "
fi
}

function redis_start()
{
cd $REDIS_DIR
echo >nohup.out
nohup redis-server &
sleep 1
redis_pid=$(ps -ef | grep redis-server | grep 'hmcl_ad' | head -1 |  awk '{print $2}')
if [ -z "$redis_pid" ]
then
        echo "Warning : redis PID not found. please check if process is already running!."
else
        echo "redis started with pid $redis_pid "
fi
}


function guni_status()
{
gunicorn_pid=$(pgrep -af flask_server:app | head -1 |  awk '{print $1}')
if [ -z "$gunicorn_pid" ]
then
        echo "gunicorn is not running!."
else
        echo "gunicorn is running"
fi
}

function redis_status()
{
redis_pid=$(ps -ef | grep redis-server | grep 'hmcl_ad' | head -1 |  awk '{print $2}')
if [ -z "$redis_pid" ]
then
        echo "redis is not running!."
else
        echo "redis is running"
fi

}

FLASK_DIR='/datadisk/CODE_MAIN/'
REDIS_DIR='/datadisk/CODE_MAIN/redis/'
cd $FLASK_DIR
echo ""
echo ""
echo ""
if [ "$1" == "gstart" ]
then
        guni_start
elif [ "$1" == "gstop" ]
then
        guni_stop
elif [ "$1" == "gstatus" ]
then
        guni_status

else
        echo "Suppoorted arguments:"
        echo "gstart : start gunicorn server"
        echo "gstop : stop gunicorn server"
	echo "gstatus : status of the gunicorn server"
        echo
        echo
        echo "r@j_2.2"
fi
echo ""
echo ""
