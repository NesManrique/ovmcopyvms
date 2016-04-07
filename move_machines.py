#!/usr/bin/python
#
# Script para mover maquinas virtuales o templates entre repositorios
# que no son alcanzables por servidores en diferentes server pools.
#
# Usage: ./move_machines.py [-h|-t|--template] <uuid repo origen> <uuid vm o template> <IP o hostname destino> <uuid repo destino>
#
# Parametros:
# arg1: uuid del repositorio origen
# arg2: uuid de la maquina virtual o template
# arg3: IP o hostname destino
# arg4: uuid del repositorio destino
#
# Logica del script:
# - Generar uuids nuevos para la maquina virtual y discos asociados.
# - Mueve los archivos del repo origen al destino usando scp/rsync.
# - Reemplaza los uuids de los nombres de los discos y en el archivo de la vm
#   en el repositorio destino.
#

import optparse, uuid, re, os

usage = "Usage: %prog [-h|-t|--template] <uuid repo origen>  <uuid vm o template> <IP o hostname destino> <uuid repo destino>"
parser = optparse.OptionParser(usage=usage)

parser.add_option('-t', '--template',
    action="store_true", dest="template",
    help="se movera el objeto como un template", default=False)

options, args = parser.parse_args()

if 4 > len(args) or len(args) >= 5:
    print usage
    exit(1)


def generate_uuid(dash=False):
    if dash:
        return str(uuid.uuid4())
    else:
        return uuid.uuid4().hex

def escape_str(string):
    return string.replace("/","\/").replace(".","\.").replace("[","\[").replace("]","\]").replace("'","'\\''")

# Rutas origen

path_repo_source = "/OVS/Repositories/"+args[0]
path_config_file_source = ''
if options.template:
    path_config_file_source = path_repo_source+"/Templates/"+args[1]+"/vm.cfg"
else:
    yes = set(['si','s', ''])
    no = set(['no','n'])

    while True:
        print "\nSegun las opciones desea copiar una VM. Se aseguro de que la maquina virtual se encuentra apagada? [si/no]"
        choice = raw_input().lower()
        if choice in yes:
            path_config_file_source = path_repo_source+"/VirtualMachines/"+args[1]+"/vm.cfg"
            break
        elif choice in no:
            print "\nEjecute el script cuando este seguro de que ha apagado la maquina virtual que desea mover.\n\n"
            exit(0)
        else:
            print "Por favor responda con 'si' o 'no'"

print "ahnosi "+path_config_file_source

path_dir_discos_source = path_repo_source+"/VirtualDisks/"

# Rutas destino

vm_uuid_dest_dash = generate_uuid(True)
vm_uuid_dest_nodash = vm_uuid_dest_dash.replace('-','')

path_repo_dest = "/OVS/Repositories/"+args[3]
path_config_file_dest = ''
if options.template:
    path_config_file_dest = path_repo_dest+"/Templates/"+vm_uuid_dest_nodash+"/vm.cfg"
else:
    path_config_file_dest = path_repo_dest+"/VirtualMachines/"+vm_uuid_dest_nodash+"/vm.cfg"
path_dir_discos_dest = path_repo_dest+"/VirtualDisks/"

# Lista de path de discos del template o vm en el origen
try:
    config_file = open(path_config_file_source).read()
except IOError:
    print "No se encontro el archivo de configuracion. Si es un template debe especificarse en las opciones del script."
    print usage
    exit(1)
else:
    disks_stanza_source = re.search(r'disk.*]', config_file).group(0)

path_discos_source = re.findall(r'(\/OVS\/Repositories\/[0-9a-f]*\/VirtualDisks\/[0-9a-f]*\.img)', disks_stanza_source)

# Lista de path de discos del template o vm en el destino

path_discos_dest = []

for p in path_discos_source:
    path_discos_dest.append(re.sub(r'\/OVS\/Repositories\/[0-9a-f]*\/VirtualDisks\/[0-9a-f]*\.img',
                            r"/OVS/Repositories/"+args[3]+"/VirtualDisks/"+generate_uuid()+".img", p))

splitted_stanza = re.split(r'\/OVS\/Repositories\/[0-9a-f]*\/VirtualDisks\/[0-9a-f]*\.img', disks_stanza_source)

disks_stanza_dest = "".join([a+b for a,b in zip(splitted_stanza,path_discos_dest)])+splitted_stanza[-1]

# Copiar archivo de configuracion al servidor remoto

print "Creando carpeta de configuracion '"+path_config_file_dest[:-7]+"' en "+args[2]
os.system('ssh '+args[2]+' mkdir '+path_config_file_dest[:-7])
print " "

print "Copiando archivo de configuracion..."
os.system('scp '+path_config_file_source+' '+args[2]+':'+path_config_file_dest)
print " "

print "Archivo de configuracion copiado a la siguiente ruta del servidor "+args[2]
os.system('ssh '+args[2]+' ls '+path_config_file_dest)
print " "

print "Modificando uuids en el archivo de configuracion\n"
print "UUID nuevo para la VM: \n"+vm_uuid_dest_dash+"\n"
os.system('ssh '+args[2]+" \"sed -i 's/^uuid =.*$/uuid = \\x27"+vm_uuid_dest_dash+"\\x27/' "+path_config_file_dest+'"')
os.system('ssh '+args[2]+" \"sed -i 's/^name =.*$/name = \\x27"+vm_uuid_dest_nodash+"\\x27/' "+path_config_file_dest+'"')

print "UUIDs nuevos para los discos: \n"+disks_stanza_dest+"\n"
os.system('ssh '+args[2]+" \"sed -i 's/"+escape_str(disks_stanza_source)+"/"+escape_str(disks_stanza_dest)+"/' "+path_config_file_dest+'"')

print "Verificando lineas modificadas en el archivo de configuracion"
os.system('ssh '+args[2]+' \"egrep \'^(name|disk|uuid) =.*$\' '+path_config_file_dest+'"')
print " "

# Copiar archivos de Discos

x = 0
num_disks = len(path_discos_dest)
print "Copiando "+str(num_disks)+" archivos de discos virtuales a "+args[2]+", esto puede tomar un tiempo considerable..."

while x < num_disks:
    print "Copiando disco \nOrig:"+path_discos_source[x]+"\nDest:"+path_discos_dest[x]+"\n"
    os.system('rsync -aS '+path_discos_source[x]+' '+args[2]+':'+path_discos_dest[x])
    x = x+1

print "Verificando que los archivos de todos los discos existen en el servidor remoto\n"
for disk in path_discos_dest:
    os.system('ssh '+args[2]+' ls '+disk)

if options.template:
    print "\nFin de la copia del Template al servidor "+args[2]
    print "Refresque el repositorio destino en el OVM Manager y renombre los discos.\n\n"
else:
    print "\nFin de la copia de la VM al servidor "+args[2]+"\n\n"
    print "Refresque el repositorio destino en el OVM Manager, renombre los discos, migre al server pool deseado y encienda la VM.\n\n"
