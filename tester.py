from scapy.all import get_working_ifaces

for i in get_working_ifaces():
    print(f"{i.name}  =>  {i.description}")
