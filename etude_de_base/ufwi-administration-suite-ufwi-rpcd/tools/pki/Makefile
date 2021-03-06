
EXTRA_DIST = gen_certs.sh gen_config.sh gen_server_cnf.sh gen_user_cnf.sh

KEY_SIZE = 1024
CA_PASS = mypassword
CA_DAYS = 7000
CERT_DAYS = 3650
CERT_PASS = weak
CRL_NAME = crl.pem
CRL_DAYS = 30

CERT_TYPE = server

CA_CLI = openssl ca -passin pass:$(CA_PASS) -batch -notext -config openssl.cnf -cert CA.crt -keyfile CA.key

# CA creation
CA: openssl.cnf testCA CA.crt

gen_certs: gen_certs.sh
	./gen_certs.sh

testCA:
	mkdir testCA/{,certs,crl,newcerts,private}
	echo '01' > ./testCA/serial
	echo '01' > ./testCA/crlnumber
	touch ./testCA/index.txt

CA.crt: CA.csr
	openssl req -x509 -config openssl.cnf -extensions v3_ca -passin pass:$(CA_PASS) -passout pass:$(CA_PASS) -key CA.key -in CA.csr -out CA.crt -days $(CA_DAYS)


CA.csr: CA.key openssl.cnf
	openssl req -new -passin pass:$(CA_PASS) -passout pass:$(CA_PASS) -config openssl.cnf -batch -key CA.key -out CA.csr -days $(CA_DAYS)

CA.key:
	openssl genrsa -des3 -passout pass:$(CA_PASS) -out CA.key $(KEY_SIZE)

# certificates generation
cert: req
	[ "x$(NAME)" != "x" ] || exit 1; \
	$(CA_CLI) -extensions usr_cert -policy policy_anything -days $(CERT_DAYS) -out $(NAME).crt -infiles $(NAME).csr


req: key gen_$(CERT_TYPE)_cnf.sh
	[ "x$(NAME)" != "x" ] || exit 1; \
	./gen_$(CERT_TYPE)_cnf.sh "$(NAME)"; \
	openssl req -new -config $(CERT_TYPE).cnf -batch -key $(NAME).key -out $(NAME).csr -days $(CERT_DAYS) ; \
	rm -f $(CERT_TYPE).cnf

key: CA
	[ "x$(NAME)" != "x" ] || exit 1; \
	openssl genrsa -out $(NAME).key

# Certificates revocation

revoke: CA
	[ "x$(NAME)" != "x" ] || exit 1; \
	[ -e "$(NAME)".crt ] || exit 2; \
	$(CA_CLI) -revoke $(NAME).crt

gencrl: CA
	$(CA_CLI) -gencrl -crldays $(CRL_DAYS) -out $(CRL_NAME)

# Misc stuff
openssl.cnf: gen_config.sh
	./gen_config.sh

clean:
	rm -f *.csr user.cnf server.cnf

distclean: clean
	rm -f *.{crt,key} crl.pem openssl.cnf
	rm -rf testCA

.PHONY: CA CA_dirs
