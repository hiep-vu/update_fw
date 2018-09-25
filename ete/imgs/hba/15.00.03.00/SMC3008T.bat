@echo off
sas3flsh -o -e 7
cls
sas3flsh -f 3008IT15.rom
sas3flsh -b mptsas3.rom
sas3flsh -b mpt3x64.rom
cls
sas3flsh -o -sasaddhi 5003048
