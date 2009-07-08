Index: update_trango.pl
===================================================================
RCS file: /cvs/scripts/Admin scripts/Trango_Update/update_trango.pl,v
retrieving revision 1.32
retrieving revision 1.33
diff -u -r1.32 -r1.33
--- update_trango.pl	7 Feb 2007 22:17:52 -0000	1.32
+++ update_trango.pl	7 Feb 2007 23:21:26 -0000	1.33
@@ -1,5 +1,5 @@
 #!/usr/bin/perl
-# $RedRiver: update_trango.pl,v 1.32 2007/02/07 22:17:52 andrew Exp $
+# $RedRiver: update_trango.pl,v 1.33 2007/02/07 23:21:26 andrew Exp $
 ########################################################################
 # update_trango.pl *** Updates trango hosts with a new firmware
 #
@@ -167,9 +167,12 @@
                 $host->{retry}--;
             }
             else {
-                $l->sp("Failed");
+                $l->sp("Failed! - Bye $host->{name}");
+                $l->e("Error updating $firmware_type on $host->{name}" . 
+                    "(try $host->{tries})");
                 $t->bye;
-                next;
+                # don't try any other firmware, don't want to reboot
+                last;
             }
 
         }
@@ -339,6 +342,7 @@
 #use YAML;
 use constant LOG_PRINT => 128;
 use constant LOG_SAVE  => 64;
+use constant LOG_ERR   => 1;
 
 DESTROY {
     my $self = shift;
@@ -378,6 +382,12 @@
     return $self->mylog( $m, LOG_SAVE | LOG_PRINT );
 }
 
+sub e {
+    my $self = shift;
+    my $m    = shift;
+    return $self->mylog( $m, LOG_ERR );
+}
+
 sub mylog {
     my $self = shift;
 
@@ -413,6 +423,11 @@
         print $MYLOG ( scalar gmtime ), "\t", $thing, "\n"
           or die "Couldn't print to MYLOG: $!";
         flock( $MYLOG, LOCK_UN );
+    }
+
+    if ( $which & LOG_ERR ) {
+        # XXX Could tie in here to handle some sort of notifications.
+        print STDERR $thing, "\n";
     }
 }
 
