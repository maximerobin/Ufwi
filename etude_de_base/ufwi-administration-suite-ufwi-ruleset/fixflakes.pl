#!/usr/bin/perl -w
#
# Usage: ./pyflakes.sh | ./fixflakes.pl
#
use strict;

while(<>)
{
	if(/^([^:]*):([0-9]*): \'([^\']*)\' imported but unused$/)
	{
		my ($file, $line, $name) = ($1, $2, $3);
		print "Fixing unused import $name in file $file, line $line\n";

		open(FILE, $file) || die "Unable to open file $file.\n";

		my @lines = <FILE>;

		if(! $lines[$line-1] =~ /^from/)
		{
			print STDERR "Don't know how to handle this line: $lines[$line-1]\n";
			next;
		}

		if($lines[$line-1] =~ /($name[ ]*,)/)
		{
			$lines[$line-1] = "$`$'";
		}
		elsif($lines[$line-1] =~ /(,[ ]*$name[ ]*)$/)
		{
			$lines[$line-1] = "$`$'";
		}
		elsif($lines[$line-1] =~ /^from [^ ]* import $name$/)
		{
			$lines[$line-1] = "";
		}
		else
		{
			print STDERR "Don't know how to handle this line: $lines[$line-1]\n";
			next;
		}

		open(FILE, '>', $file) || die "Unable to write into $file.\n";
		print FILE @lines;
	}
}

