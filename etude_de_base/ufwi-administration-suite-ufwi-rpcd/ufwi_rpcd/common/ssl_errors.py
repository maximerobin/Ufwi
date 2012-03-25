
"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

from ufwi_rpcd.common import tr

X509_V_OK = 1
X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT = 2
X509_V_ERR_UNABLE_TO_GET_CRL = 3
X509_V_ERR_UNABLE_TO_DECRYPT_CERT_SIGNATURE = 4
X509_V_ERR_UNABLE_TO_DECRYPT_CRL_SIGNATURE = 5
X509_V_ERR_UNABLE_TO_DECODE_ISSUER_PUBLIC_KEY = 6
X509_V_ERR_CERT_SIGNATURE_FAILURE = 7
X509_V_ERR_CRL_SIGNATURE_FAILURE = 8
X509_V_ERR_CERT_NOT_YET_VALID = 9
X509_V_ERR_CERT_HAS_EXPIRED = 10
X509_V_ERR_CRL_NOT_YET_VALID = 11
X509_V_ERR_CRL_HAS_EXPIRED = 12
X509_V_ERR_ERROR_IN_CERT_NOT_BEFORE_FIELD = 13
X509_V_ERR_ERROR_IN_CERT_NOT_AFTER_FIELD = 14
X509_V_ERR_ERROR_IN_CRL_LAST_UPDATE_FIELD = 15
X509_V_ERR_ERROR_IN_CRL_NEXT_UPDATE_FIELD = 16
X509_V_ERR_OUT_OF_MEM = 17
X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT = 18
X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN = 19
X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY = 20
X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE = 21
X509_V_ERR_CERT_CHAIN_TOO_LONG = 22
X509_V_ERR_CERT_REVOKED = 23
X509_V_ERR_INVALID_CA = 24
X509_V_ERR_PATH_LENGTH_EXCEEDED = 25
X509_V_ERR_INVALID_PURPOSE = 26
X509_V_ERR_CERT_UNTRUSTED = 27
X509_V_ERR_CERT_REJECTED = 28
X509_V_ERR_SUBJECT_ISSUER_MISMATCH = 29
X509_V_ERR_AKID_SKID_MISMATCH = 30
X509_V_ERR_AKID_ISSUER_SERIAL_MISMATCH = 31
X509_V_ERR_KEYUSAGE_NO_CERTSIGN = 32
X509_V_ERR_UNABLE_TO_GET_CRL_ISSUER = 33
X509_V_ERR_UNHANDLED_CRITICAL_EXTENSION = 34
X509_V_ERR_KEYUSAGE_NO_CRL_SIGN = 35
X509_V_ERR_UNHANDLED_CRITICAL_CRL_EXTENSION = 36
X509_V_ERR_INVALID_NON_CA = 37
X509_V_ERR_PROXY_PATH_LENGTH_EXCEEDED = 38
X509_V_ERR_KEYUSAGE_NO_DIGITAL_SIGNATURE = 39
X509_V_ERR_PROXY_CERTIFICATES_NOT_ALLOWED = 40
X509_V_ERR_INVALID_EXTENSION = 41
X509_V_ERR_INVALID_POLICY_EXTENSION = 42
X509_V_ERR_NO_EXPLICIT_POLICY = 43
X509_V_ERR_UNNESTED_RESOURCE = 44
X509_V_ERR_APPLICATION_VERIFICATION = 50

def X509_verify_cert_error_string(err):
    str_err = {
            X509_V_OK : tr("OK"),
            X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT : tr("unable to get issuer certificate"),
            X509_V_ERR_UNABLE_TO_GET_CRL : tr("unable to get certificate CRL"),
            X509_V_ERR_UNABLE_TO_DECRYPT_CERT_SIGNATURE : tr("unable to decrypt certificate signature"),
            X509_V_ERR_UNABLE_TO_DECRYPT_CRL_SIGNATURE : tr("unable to decrypt CRL signature"),
            X509_V_ERR_UNABLE_TO_DECODE_ISSUER_PUBLIC_KEY : tr("unable to decode issuer public key"),
            X509_V_ERR_CERT_SIGNATURE_FAILURE : tr("certificate signature failure"),
            X509_V_ERR_CRL_SIGNATURE_FAILURE : tr("CRL signature failure"),
            X509_V_ERR_CERT_NOT_YET_VALID : tr("certificate is not yet valid"),
            X509_V_ERR_CRL_NOT_YET_VALID : tr("CRL is not yet valid"),
            X509_V_ERR_CERT_HAS_EXPIRED : tr("certificate has expired"),
            X509_V_ERR_CRL_HAS_EXPIRED : tr("CRL has expired"),
            X509_V_ERR_ERROR_IN_CERT_NOT_BEFORE_FIELD : tr("format error in certificate notBefore field"),
            X509_V_ERR_ERROR_IN_CERT_NOT_AFTER_FIELD : tr("format error in certificate notAfter field"),
            X509_V_ERR_ERROR_IN_CRL_LAST_UPDATE_FIELD : tr("format error in CRL lastUpdate field"),
            X509_V_ERR_ERROR_IN_CRL_NEXT_UPDATE_FIELD : tr("format error in CRL nextUpdate field"),
            X509_V_ERR_OUT_OF_MEM : tr("out of memory"),
            X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT : tr("self signed certificate"),
            X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN : tr("self signed certificate in certificate chain"),
            X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY : tr("unable to get local issuer certificate"),
            X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE : tr("unable to verify the first certificate"),
            X509_V_ERR_CERT_CHAIN_TOO_LONG : tr("certificate chain too long"),
            X509_V_ERR_CERT_REVOKED : tr("certificate revoked"),
            X509_V_ERR_INVALID_CA : tr("invalid CA certificate"),
            X509_V_ERR_INVALID_NON_CA: tr("invalid non-CA certificate (has CA markings)"),
            X509_V_ERR_PATH_LENGTH_EXCEEDED : tr("path length constraint exceeded"),
            X509_V_ERR_PROXY_PATH_LENGTH_EXCEEDED : tr("proxy path length constraint exceeded"),
            X509_V_ERR_PROXY_CERTIFICATES_NOT_ALLOWED : tr("proxy certificates not allowed, please set the appropriate flag"),
            X509_V_ERR_INVALID_PURPOSE : tr("unsupported certificate purpose"),
            X509_V_ERR_CERT_UNTRUSTED : tr("certificate not trusted"),
            X509_V_ERR_CERT_REJECTED : tr("certificate rejected"),
            X509_V_ERR_APPLICATION_VERIFICATION : tr("application verification failure"),
            X509_V_ERR_SUBJECT_ISSUER_MISMATCH : tr("subject issuer mismatch"),
            X509_V_ERR_AKID_SKID_MISMATCH : tr("authority and subject key identifier mismatch"),
            X509_V_ERR_AKID_ISSUER_SERIAL_MISMATCH : tr("authority and issuer serial number mismatch"),
            X509_V_ERR_KEYUSAGE_NO_CERTSIGN : tr("key usage does not include certificate signing"),
            X509_V_ERR_UNABLE_TO_GET_CRL_ISSUER : tr("unable to get CRL issuer certificate"),
            X509_V_ERR_UNHANDLED_CRITICAL_EXTENSION : tr("unhandled critical extension"),
            X509_V_ERR_KEYUSAGE_NO_CRL_SIGN : tr("key usage does not include CRL signing"),
            X509_V_ERR_KEYUSAGE_NO_DIGITAL_SIGNATURE : tr("key usage does not include digital signature"),
            X509_V_ERR_UNHANDLED_CRITICAL_CRL_EXTENSION : tr("unhandled critical CRL extension"),
            X509_V_ERR_INVALID_EXTENSION : tr("invalid or inconsistent certificate extension"),
            X509_V_ERR_INVALID_POLICY_EXTENSION : tr("invalid or inconsistent certificate policy extension"),
            X509_V_ERR_NO_EXPLICIT_POLICY : tr("no explicit policy"),
            X509_V_ERR_UNNESTED_RESOURCE : tr("RFC 3779 resource not subset of parent's resources"),
    }
    if err in str_err:
        return str_err[err]
    return tr("Unknown SSL error code: %i") % err

