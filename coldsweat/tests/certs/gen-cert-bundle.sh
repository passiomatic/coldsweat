#!/bin/bash

usage(){
	echo ""
	echo "  By using this script, you will:"
	echo "    1) Generate a new sample certificate authority ('coldsweat-ca-cert.crt')"
	echo "       and server certificate ('coldsweat-server-cert.crt') for Coldsweat."
	echo "    2) Delete the previous samples."
	echo ""
	echo "  Usage:"
	echo "    bash gen-cert-bundle.sh [OPTIONS]"
	echo ""
	echo "  Options:"
	echo "    --rip <ip-alt>     Optional IP address to put into Subject Alternative Name"
	echo "                       (SAN) extension of the server certificate."
	echo "    --rdns <dns-alt>   Optional DNS name to put into Subject Alternative Name"
	echo "                       (SAN) extension of the server certificate."
	echo "    -h, --help         Optional. Print this small tutorial."
	echo ""
	echo "  Server certificate's SAN extension will mirror the subject's Common Name by"
	echo "  default ('127.0.0.1') so use '-rip' and '-rdns' only to create a certificate"
	echo "  to test remote access. Both options may be used simultaneously."
	echo ""
	echo "  Coldsweat is already configured to point to the generated files so there is"
	echo "  one more thing to do: put the generated CA into your trust store (e.g., the"
	echo "  browser, ideally Firefox). Otherwise, Coldsweat should print a client error:"
	echo "    'SSLError: [SSL: TLSV1_ALERT_UNKNOWN_CA] tlsv1 alert unknown ca'"
	echo "  In Firefox, you'll find the root in the 'Authorities' tab, under:"
	echo "    'Software tests @all.devs.com'"
	echo "  Please understand that pushing the re-generated samples to GitHub means that"
	echo "  everyone else will NOT be able to verify the server certificate anymore, so"
	echo "  don't do that needlessly!"
	echo ""
	echo "  After the server certificate will have been generated, we will safely delete"
	echo "  the CA's private key (so that developers won't poison their trust store by"
	echo "  importing the CA). Whatever you do, PLEASE MAKE SURE THE CA'S PRIVATE KEY IS"
	echo "  SAFELY DELETED BEFORE YOU PUSH TO GITHUB!"
	echo ""
	echo "  We assume that the following software is installed and available:"
	echo "    - findutils (standard *Nix tools)"
	echo "    - OpenSSL"
	echo "    - BCWipe"
	echo ""
	echo "  Script was developed and tested with OpenSSL v1.0.2k but should be portable"
	echo "  to other versions, both in the past and future."
	echo ""
}

# Parsing of arguments taken from:
#	http://stackoverflow.com/a/14203146
# Notes:
#	- Consume one arg per pass: -gt 0
#	- Consume two args per pass: -gt 1
while [[ $# -gt 0 ]]
do
	# get and handle the next option
	opt="$1"
	case $opt in
    	-h|--help)
			usage
			exit 0
			;;
		--rip)
			if [ -z "$2" ]; then
				usage
				exit 1
			else
				ALT_IP="$2"
				shift # release $2
			fi
			;;
		--rdns)
			if [ -z "$2" ]; then
				usage
				exit 2
			else
				ALT_DNS="$2"
				shift # release $2
			fi
			;;
		*)
			usage
			exit 3
			;;
	esac
	shift # release 'opt'
done

# test whether we can find out OpenSSL's installation prefix:
<<NOT_NEEDED_ANYMORE
OPENSSL_DIR=$(openssl version -a | grep OPENSSLDIR | sed -n 's/^OPENSSLDIR: "\(.*\)"$/\1/p')
RET_CODE=$?
if [ "$RET_CODE" -ne 0 ] || [ -z "$OPENSSL_DIR" ]; then
	echo -e "Error: could not determine OpenSSL's installation prefix."
	exit 3
else
	echo -e "\n  OpenSSL's installation prefix:"
	echo -e "    $OPENSSL_DIR"
fi
NOT_NEEDED_ANYMORE

# test whether the 'find' and 'bcwipe' commands are available:
if [ -z "$(which find)" ]; then
	echo -e "\n  Error: the 'find' command is unavailable."
	exit 4
fi
if [ -z "$(which bcwipe)" ]; then
	echo -e "\n  Error: BCWipe is unavailable."
	exit 4
fi

# before we begin, print some important info & warnings:
echo -e "\n  Guidance:"
echo -e "    For your convenience, everything has been pre-configured. Let's play an"
echo -e "    Enter/Paste game. You either paste a passphrase or hit the Enter key."
echo -e "  Notes:"
echo -e "    1. Keep track of both passphrases (you will be prompted for them later)."
echo -e "    2. It's more convenient for both passphrases to be identical."
echo -e "    3. It's been a pain to discover how to do all of this, so I hope you"
echo -e "       appreciate it :)."

# determine the directory of this script and go inside:
SELF_PATH=$(dirname $0)
cd "$SELF_PATH"

# cleanup from any previous runs (except this script of course):
find . -name "coldsweat-*" -exec rm {} \;

#########################################
# SETUP VARIABLES, READ & ADJUST CONFIG
#########################################

# CA files:
CA_PRIV=coldsweat-ca-priv.pem.enc
CA_REQ=coldsweat-ca-req.csr
CA_CERT=coldsweat-ca-cert.crt
CA_SRL=coldsweat-ca-cert.srl
CA_CNF=coldsweat-ca-config.cnf

# server certificate files:
SRVR_PRIV=coldsweat-server-priv.pem.enc
SRVR_PRIV_FINAL=coldsweat-server-priv.pem
SRVR_REQ=coldsweat-server-req.csr
SRVR_CERT=coldsweat-server-cert.crt
SRVR_CNF=coldsweat-server-config.cnf

# how long both the generated certificates will stay valid (cca 100 years):
DAYS_VALID=36500

# configurations for CSRs:
CONFIG_CA="$(cat csr-generic-config.txt)"
CONFIG_SRVR="$CONFIG_CA"
CONFIG_SRVR=$(echo "$CONFIG_SRVR" | sed 's/^0.organizationName_default.*$/0.organizationName_default = A Coldsweat server/')
CONFIG_SRVR=$(echo "$CONFIG_SRVR" | sed 's/^commonName_default.*$/commonName_default = 127.0.0.1/')
CONFIG_SRVR=$(echo "$CONFIG_SRVR" | sed 's/^# IP.1.*$/IP.1 = 127.0.0.1/')
if [ ! -z "$ALT_IP" ]; then
	CONFIG_SRVR=$(echo "$CONFIG_SRVR" | sed "s/^# IP.2.*$/IP.2 = $ALT_IP/")
fi
if [ ! -z "$ALT_DNS" ]; then
	CONFIG_SRVR=$(echo "$CONFIG_SRVR" | sed "s/^DNS.1.*$/DNS.1 = $ALT_DNS/")
fi

#########################################
# GENERATE SELF-SIGNED AUTHORITY
#########################################
echo -e "\n[Generating self-signed certificate authority (CA)...]"

echo -e "--- Generating private key for the CA...]"
openssl genrsa -aes256 -out $CA_PRIV 2048
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

echo -e "--- Generating certificate signing request (CSR) against the CA's private key...]"
openssl req -new -key $CA_PRIV -config <(echo "$CONFIG_CA") -out $CA_REQ
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

echo -e "--- Generating CA certificate from the CSR...]"
# first write the (possibly modified) generic config into a temporary file:
echo "$CONFIG_CA" > $CA_CNF
# and then pass the appropriate config and extension section:
openssl x509 -req -days $DAYS_VALID -signkey $CA_PRIV -extensions v3_ca -extfile $CA_CNF -in $CA_REQ -out $CA_CERT
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

#########################################
# GENERATE SIGNED SERVER CERTIFICATE
#########################################
echo -e "\n[Generating self-signed server certificate...]"

echo -e "--- Generating private key for the server...]"
openssl genrsa -aes256 -out $SRVR_PRIV 2048
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

echo -e "--- Generating certificate signing request (CSR) against the server's private key...]"
openssl req -new -key $SRVR_PRIV -config <(echo "$CONFIG_SRVR") -out $SRVR_REQ
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

echo -e "--- Generating server certificate from the CSR...]"
# first write the (possibly modified) generic config into a temporary file:
echo "$CONFIG_SRVR" > $SRVR_CNF
# and then pass the appropriate config and extension section:
openssl x509 -req -days $DAYS_VALID -CA $CA_CERT -CAkey $CA_PRIV -CAcreateserial -extensions v3_req -extfile $SRVR_CNF -in $SRVR_REQ -out $SRVR_CERT
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

echo -e "--- Removing passphrase from server's private key...]"
openssl rsa -in $SRVR_PRIV -out $SRVR_PRIV_FINAL
if [ $? -ne 0 ]; then
	echo -e "\n  Error: last command didn't finish successfully... stopping."
	exit 5
fi

#########################################
# CLEANUP
#########################################

# these files are not needed anymore:
rm index.txt crlnumber.txt crl.pem rand.txt $CA_SRL $CA_REQ $SRVR_REQ $CA_CNF $SRVR_CNF &> /dev/null

# encrypted private keys are not needed anymore and need to be safely deleted:
bcwipe -fv "$CA_PRIV"
bcwipe -fv "$SRVR_PRIV"

echo -e "\n  All done!"
