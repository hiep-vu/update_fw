echo -off
sas3flash.efi -o -e 7
cls
sas3flash.efi -f 3008IT14.ROM
sas3flash.efi -b mptsas3.rom
sas3flash.efi -b mpt3x64.rom
cls
sas3flash.efi -o -sasaddhi 5003048