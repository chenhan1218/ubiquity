
# File "part/peez2/README.txt".
# "peez2" brief how-to.
# Created by Antonio Olmo <aolmo@emergya.info> on 29 july 2005.

	Description
	-----------

    "peez2" is the partition assistant made for the "Junta de Andalucía" by
"Activa Sistemas".

	Disclaimer
	----------

    This software is intended for low-level operations, and is currently being
tested by "Guadalinex 2005" development team -- although it has been written
by others. Use it at your own risk. For the moment, and as a piece of advice,
test it only with unmounted hard disks containing no important data.

	Files
	-----

libparted1.6-12_1.6.21-1.ext3bug_i386.deb: customized parted library.
peez2_0.7.8_i386.deb:                      Debian package.
peez2_0.7.8.tar.gz:                        whole development tree.

	Installation
	------------

1. Install the Debian package:
	sudo dpkg --install peez2_0.7.8_i386.deb
   Maybe you should also install or update some other packages. Usually these
   are:
	libc6    (>= 2.3.2.ds1-21)
	libntfs5 (>= 1.9.4)
2. Set "peez2" libraries directory:
	export LD_LIBRARY=/usr/lib/peez2
3. In order to check ext3 partitions with its sparse_super feature enabled,
   you will have to install the modified libpart package as well:
	sudo dpkg --install libparted1.6-12_1.6.21-1.ext3bug_i386.deb
   Then, set:
	export PT_FORCE_EXT3_SPARSE=yes

	Usage
	-----

    See [2].

	References
	----------

[1] Main source of information from "Activa Sistemas":
    http://activasistemas.com/forja/index.php/Análisis_de_particiones_-_peez2
[2] Usage: http://activasistemas.com/forja/index.php/Uso
[3] Downloads: http://activasistemas.com/forja/files/peez2

# End of file.

