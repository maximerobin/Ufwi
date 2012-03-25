#coding: utf-8
LANGUAGES = FR, = 'FR', #tuple
MAIL_SUBJECT = {
    FR: u"Erreur sur votre cluster haute disponibilité"
}
MAIL_BODY = {
    FR: u"""\
La réplication de la configuration du membre primaire de votre cluster EdenWall
haute disponibilité a entraîné une erreur sur le membre secondaire.

Nous vous recommandons de vous connecter au membre secondaire de votre
cluster haute disponibilité au moyen d'EdenWall Administration Suite
en utilisant un compte utilisateur disposant des droits d'audit et
de consulter le journal.

L'erreur à l'origine de l'envoi de cet e-mail telle qu'elle a été transmise
au membre primaire du cluster est :

%(ERROR)s

"""
}

MAIL_NOROUTE_BODY = {
    FR: u"""\
La réplication de la configuration de votre cluster EdenWall
haute disponibilité est interrompue car la liaison réseau dédiée
est indisponible.


Le message erreur à l'origine de l'envoi de cet e-mail est :

%(ERROR)s

"""
}

