#!/usr/bin/perl
# $RedRiver: su.cgi,v 1.4 2007/02/07 19:25:21 andrew Exp $
########################################################################
# su.cgi *** a CGI for Trango SU utilities.
# 
# 2007.02.07 #*#*# andrew fresh <andrew@mad-techies.org>
########################################################################
# Copyright (C) 2007 by Andrew Fresh
# 
# This program is free software; you can redistribute it and/or modify 
# it under the same terms as Perl itself.
########################################################################
use strict;
use warnings;

my $host_file = 'su.yaml';

my $default_mac  = '0001DE';
my $default_suid = 'all';
my $default_cir  = 256;
my $default_mir  = 9999;
my $Start_SUID = 3;

use CGI qw/:standard/;
use File::Basename;
use YAML qw/ LoadFile Dump /;
use Net::Telnet::Trango;

my $me = basename($0);

my $aps = get_aps($host_file);

print header,
      start_html('Trango SU Utilities'),
      h1('Trango SU Utilities');

if (param()) {

    my $AP = param('AP');

    unless (exists $aps->{$AP}) {
        print h3("AP '$AP' does not exist!");
        print end_html;
        exit;
    }

    my $sumac = param('sumac');

    $sumac =~ s/[^0-9A-Fa-f]//g;
    $sumac = uc($sumac);

    my $suid = param('suid');

    if (length $sumac == 12) {
        add_su($aps->{$AP}, $sumac);
    } elsif (length $suid) {
        testrflink($aps->{$AP}, $suid);
    } else {
        print h3("Invalid SUID '$suid' and MAC '$sumac'");
        show_form($aps, $default_mac);
    }

} else {
    show_form($aps, $default_mac);
}


print end_html;


sub get_aps
{
    my $file = shift;

    my $conf = LoadFile($file);

    my %aps;

    my @hosts;
    foreach my $ap (keys %{ $conf }) {
        next if $ap eq 'default';
		my $h = $conf->{$ap};

        if ($h->{name} =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})-(\d{1,3})/) {
            for ($2..$3) {
                my %cur_host;
                foreach my $k (keys %{ $h }) {
                    $cur_host{$k} = $h->{$k};
                }
                $cur_host{name} = $1 . $_;
                if (! grep { $cur_host{name} eq $h->{name} } values %aps) {
					my $ap_name = $ap . $_;
        			$aps{ $ap_name  } = \%cur_host;
                }
            }
        } else {
        	$aps{ $ap } = $conf->{$ap};
            push @hosts, $h;
        }
    }

    if (ref $conf->{default} eq 'HASH') {
	    foreach my $ap (keys %aps) {
            foreach my $k (keys %{ $conf->{default} }) {
                $aps{ $ap }{$k} ||= $conf->{default}->{$k};
            }
        }
    }

    return \%aps;

    return { 
        'rrlhcwap0000' => {
            name     => '192.168.1.1',
            password => 'trango',
        }
    };

}

sub show_form
{
    my $aps  = shift;

    my %cache = ();
    my @ap_names = sort {
        my @a = $a =~ /(\d+)\.(\d+)\.(\d+)\.(\d+)/;
        my @b = $b =~ /(\d+)\.(\d+)\.(\d+)\.(\d+)/;

        if (@a) {
            $cache{$a} ||= pack('C4' => @a);
        } else {
            $cache{$a} ||= lc($a);
        }
        if (@b) {
            $cache{$b} ||= pack('C4' => @b);
        } else {
            $cache{$b} ||= lc($b);
        }

        $cache{$a} cmp $cache{$b};
    } keys %{ $aps };

    print p(start_form(-method => 'GET'),
        'AP:    ', popup_menu(-name=>'AP',    -values=>\@ap_names),br,
        'SUMAC: ', textfield( -name=>'sumac', -default=>$default_mac),br,
        'SUID:  ', textfield( -name=>'suid',  -default=>$default_suid),br,
        submit,
        end_form);

    print p('Fill in the SUMAC if you wish to add an SU ',
      'or fill in the SUID to run an rflinktest.');

    return 1;
}

sub login
{
    my $host     = shift;
    my $password = shift;

    my $t = new Net::Telnet::Trango ( Timeout => 5 );

    #$t->input_log('/tmp/telnet_log');
    #$t->dump_log('/tmp/telnet_log');

    unless ($t->open( Host => $host )) {
        print h3("Error connecting!");
        $t->close;
        return undef;
    }

    unless ($t->login( $password ) ) {
        print h3("Couldn't log in: $!");
        $t->exit;
        $t->close;
        return undef;
    }

    return $t;
}

sub add_su
{
    my $ap  = shift;
    my $sumac = shift;

    my $t = login($ap->{name}, $ap->{password});

    my $cur_sus = $t->sudb_view;

    my $new_suid = next_suid($cur_sus);

    foreach my $su (@{ $cur_sus }) {
        if ($sumac eq $su->{mac}) {
            print h3("MAC '$sumac' already in AP '$ap->{name}' " . 
              "with SUID '$su->{suid}'");
            $t->exit;
            $t->close;
            return undef;
        }
    }

    unless ($t->sudb_add(
        $new_suid, 'reg', $default_cir, $default_mir, $sumac
    ) ) {
        print h3("Error adding SU!");
        $t->exit;
        $t->close;
        return undef;
    }

    my $new_sus = $t->sudb_view;
    my $added = 0;
    foreach my $su (@{ $new_sus }) {
        if ($su->{suid} == $new_suid) {
            $added = 1;
            last;
        }
    }

    unless ($added) {
        print h3("Couldn't add su id: $new_suid");
        $t->exit;
        $t->close;
        return undef;
    }

    unless ($t->save_sudb) {
        print h3("Couldn't save sudb");
        $t->exit;
        $t->close;
        return undef;
    }

    print p(
        "Added new SU with ID '$new_suid' " .
        "and MAC '$sumac' " .
        "to '$ap->{name}'.  " .
        '<a href="' . $me . '?' . 
        'AP=' . $ap->{name} . '&' . 
        'suid=' . $new_suid . 
        '">Test SU RFLink</a>'
    );

    $t->exit;
    $t->close;
    return 1;

}

sub testrflink
{
    my $ap  = shift;
    my $suid = shift;

    my $t = login($ap->{name}, $ap->{password});

    my $result = $t->su_testrflink( $suid );

    unless ($result) {
        print h3("Error testing SU rflink!");
        $t->exit;
        $t->close;
        return undef;
    }

    my @keys = ('suid', 'AP Tx', 'AP Rx', 'SU Rx');

    my @table;
    foreach my $su (@{ $result }) {
        next unless ref $su eq 'HASH';
        next unless exists $su->{suid};
        $su->{suid} =~ s/\D//g;
        next unless $su->{suid};

        push @table, td([ @{ $su }{ @keys } ]);
    }

    print table({-border=>1,-cellspacing=>0,-cellpadding=>1},
        caption($ap->{name} . ': su testrflink ' . $suid),
        Tr({-align=>'CENTER', -valign=>'TOP'},
            [ th(\@keys), @table ]
        )
    );

    $t->exit;
    $t->close;
    return 1;

}

sub next_suid
{
    my $sudb = shift;

    my $next_id = $Start_SUID;

    my %ids = map { $_->{suid} => 1 } @{ $sudb };

    my $next_key = sprintf('%04d', $next_id);
    while (exists $ids{$next_key}) {
        $next_id++;
        $next_key = sprintf('%04d', $next_id);
    }

    return $next_id;
}
