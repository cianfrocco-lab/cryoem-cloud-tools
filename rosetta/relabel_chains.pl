#!/usr/bin/perl
##
##
###############################################################################

use strict;

if ($#ARGV < 0) {
	print STDERR "usage: $0 <pdbfile>\n";
	exit -1;
}

my $ADDTER = 1;
my $CHAINBREAK_DIST = 99999.0;
my $RENUMBER_BY_CHAIN = 1;

foreach my $pdbfile (@ARGV) {

	open (PDB, $pdbfile) || die "cannot open $pdbfile";
	my $pdbout = $pdbfile;
	$pdbout =~ s/\.pdb/_r.pdb/g;
	open (PDBOUT, ">$pdbout") || die "cannot open $pdbfile";

	# read pdb file into memory
	my @pdbdata;
	while (my $line = <PDB>) {
		chomp $line;
		push @pdbdata, $line;
	}
	close PDB;

	my @chnids = ('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R',
				  'S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j',
				  'k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','1','2',
				  '3','4','5','6','7','8','9','!');

#	my @chnids = ('A','B','D','E','H','G','Q','Z');

	my $prevResId = 99999;
	my $Cpos = [0,0,0];
	my $currid = 0;
	my $innum  = -999;
	my $outnum = 0;

	foreach my $line (@pdbdata) {
		if ($line =~ /^ENDMDL/ || $line =~ /^TER/) {
			if ( $ADDTER==1 ) {
				print PDBOUT "TER   \n";
			}
			if ($outnum != 0) { $currid++; $outnum = 0; }
			next;
		}

		if ($line =~ /^CRYST1/) {
			print PDBOUT $line."\n";
			next ;
		}

		if ($line !~ /^ATOM/ && $line !~ /^HETATM/) {
			#print PDBOUT $line."\n";
			next ;
		}

		if ( substr( $line, 17, 3 ) eq "HOH" ) {
			next;
		}

		my $currpos = [ substr ($line, 30, 8) , substr ($line, 38, 8) , substr ($line, 46, 8) ];
		my $atmid = substr($line,12,4);
		my $resid = substr($line,22,4);

		## when resid drops/resets mark a new chain
		if ($resid < $prevResId) {
			if ( $ADDTER==1 ) {
				print PDBOUT "TER   \n";
			}
			if ($outnum != 0) { $currid++; $outnum = 0; }
		} else {
			## distance check?  look for prevC->thisN distance
			if ($atmid eq " C  " || $atmid eq " O3'") {
				$Cpos = [ $currpos->[0] , $currpos->[1], $currpos->[2] ];
			} elsif ($atmid eq " N  "|| $atmid eq " P  ") {
				my $dist = dist( $Cpos, $currpos );
				if ($dist > $CHAINBREAK_DIST) {
					if ( $ADDTER ) {
						print PDBOUT "TER   \n";
					}
					if ($outnum != 0) {$currid++; $outnum=0;}
				}
			}
		}
		$prevResId = $resid;

		if ($RENUMBER_BY_CHAIN == 1) {
			if ($resid != $innum) {
				$innum = int($resid);
				$outnum++;
			}
			#substr ($line, 22, 4) = sprintf "%4d" , $outnum;
		}

		if ($currid > $#chnids) { $currid = $#chnids; }

		substr($line,21,1) = $chnids[ $currid ];

		print  PDBOUT $line."\n";
	}

}


sub dist {
	my ($x, $y) = @_;
	my $z = [ $x->[0]-$y->[0] , $x->[1]-$y->[1] , $x->[2]-$y->[2] ];
	return sqrt( $z->[0]*$z->[0] + $z->[1]*$z->[1] + $z->[2]*$z->[2] );
}
