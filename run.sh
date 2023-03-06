cd ~/fpgroup
git reset --hard
git fetch
git pull
clear
source ../config.ini
python3 -m pip install --upgrade -q -r requirements.txt
python3 main.py