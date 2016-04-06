# ovmcopyvms
## Script para copiar vms y templates entre repositorios no compartidos

El script debe correr desde un servidor con acceso al repositorio origen, usando el usuario root y debe existir una relacion de confianza de este usuario entre los servidores con acceso a ambos repositorios, origen y destino.

**Uso: ./move_machines.py [-h|-t|--template] uuid_repo_origen uuid_vm_o_template IP_o_hostname_destino uuid_repo_destino**

La lógica del script genera UUIDs nuevos para la maquina virtual o template y los discos asociados, copia el archivo de configuracion de la maquina/template y los archivos de los discos al repositorio destino usando rsync/scp y reemplaza los uuids correspondientes en el archivo de configuración en el destino para poder iniciar o desplegar el objeto correctamente.

Para mas información sobre el procedimiento revisar el [siguiente blog](https://ericsteed.wordpress.com/2015/09/15/copying-virtual-machines-between-repositories-in-oracle-vm-for-x8).
