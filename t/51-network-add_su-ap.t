#!perl -T
# $RedRiver: 51-network-add_su-ap.t,v 1.8 2007/02/06 20:59:10 andrew Exp $

use Test::More tests => 17;
use File::Spec;

BEGIN {
	use_ok( 'Net::Telnet::Trango' );
}

diag("51: AP tests when adding an SU to an AP");

my $cfg_file = File::Spec->catfile('t', 'tests.cfg');
my ($cir, $mir, $new_mir) = (128, 256, 1024);

SKIP: {
    my $skipped = 16;
    my %cfg;
    if (-e $cfg_file) {
        if (open my $fh, $cfg_file) {
            while (<$fh>) {
                chomp;
                my ($key, $value) = split /\t/, $_, 2;
                $cfg{$key} = $value;
            }
            close $fh;
        }
    }

    my $type = 'AP';
    my ($host, $pass, $su_id, $su_mac);

    if ($cfg{$type} && $cfg{$type} =~ /^(\d+\.\d+\.\d+.\d+)$/) {
        $host = $1;
    }

    skip 'No valid ' . $type . ' in config file',        $skipped unless $host; 

    if ($cfg{$type . '_PASSWD'} && $cfg{$type . '_PASSWD'} =~ /^(.*)$/) {
        $pass = $1;
    }

    skip 'No valid ' . $type . '_PASSWD in config file', $skipped unless $pass;

    if ($cfg{SU_ID} && $cfg{SU_ID} =~ /^(\d+)$/) {
        $su_id= $1;
    }

    skip 'No valid SU_ID in config file', $skipped unless $su_id;

    if ($cfg{SU_MAC} && length $cfg{SU_MAC} >= 12 && $cfg{SU_MAC} =~ /^(.*)$/) {
        $su_mac = $1;
    }

    skip 'No valid SU_MAC in config file', $skipped unless $su_mac;

    my $t;
    ok($t = Net::Telnet::Trango->new(), "Instantiating object");

    ok($t->open($host), "Opening connection to $host");

    ok($t->is_connected, "connected");

    ok($t->login($pass), "Logging in");

    ok($t->logged_in, "logged in");

    my $sudb;
    if ((!ok($sudb = $t->sudb_view, "Getting sudb"))
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    my $in_sudb = 0;
    foreach my $su (@{ $sudb }) {
        if ($su_id == $su->{suid}) {
            if (lc($su_mac) eq lc($su->{mac})) {
                $in_sudb = 1;
            } else {
                $in_sudb = -1;
                diag("Incorrect mac for SUID $su_id");
                diag("  Should be $su_mac");
                diag("  Really is $su->{mac}");
            }
            last;
        }
    }

    if ($in_sudb) {
        diag("Removing suid $su_id from AP");
        if ( (! $t->sudb_delete($su_id)) 
          && $t->last_error ) {
            diag('ERR: ' . $t->last_error);
        }
    }


    if ( (! ok($t->sudb_add($su_id, 'reg', $cir, $mir, $su_mac), "Adding su")) 
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    $sudb = [];
    if ((!ok($sudb = $t->sudb_view, "Getting sudb"))
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    $in_sudb = 0;
    my $su_mir = 0;
    foreach my $su (@{ $sudb }) {
        if ($su_id == $su->{suid}) {
            if (lc($su_mac) eq lc($su->{mac})) {
                $su_mir = $su->{mir};
                $in_sudb = 1;
            } else {
                $in_sudb = -1;
                diag("Incorrect mac for SUID $su_id");
                diag("  Should be $su_mac");
                diag("  Really is $su->{mac}");
            }
            last;
        }
    }

    is($in_sudb, 1, "Correct SU is in SUDB");

    if ( (! ok($t->save_sudb, "Saving sudb")) 
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    is($mir, $su_mir, "SU has correct mir");

    if ( (! ok($t->sudb_modify($su_id, 'mir', $new_mir), "modifying su mir")) 
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    $sudb = [];
    if ((!ok($sudb = $t->sudb_view, "Getting sudb"))
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    $su_mir = 0;
    foreach my $su (@{ $sudb }) {
        if ($su_id == $su->{suid}) {
            $su_mir = $su->{mir};
            last;
        }
    }

    is($new_mir, $su_mir, "SU has new mir");

    if ( (! ok($t->save_sudb, "Saving sudb")) 
      && $t->last_error ) {
        diag('ERR: ' . $t->last_error);
    }

    ok($t->bye, "Goodbye");
}
