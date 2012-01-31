La création d'un composant NuCentral se fait en deux étapes : écriture du code
source, puis ajout dans votre configuration NuCentral.

Écrire un nouveau composant NuCentral
=====================================

Pour des raisons pratiques, il faut que le nom du composant doit être composé
de lettres minuscules et des traits de soulignement (underscore, « _ »).
Exemples : nulog, nuauth_command, etc.

Commencez par crée un répertoire portant le nom de votre composant. Puis
créez un fichier __init__.py dans ce dossier. Exemple avec un module
"nuauth" : ::

    $ mkdir nuauth
    $ cd nuauth
    $ cat >__init__.py <<EOF
    from nucentral import Component
    class Nuauth(Component):
        NAME = "nuauth"
        VERSION = "1.0"
        API_VERSION = 1
    EOF

Maintenant, vous pouvez ajouter des méthodes pour chaque services. Le nom de
la méthode est important :

 * Méthode init() : fonction appelée lorsque le composant est crée, elle
   reçoit en argument l'objet « core » (nucentrall.core.Core)
 * Préfixe « service_ » : service asynchrone
 * Préfixe « page_ » : un page dans l'interface web

Mise à part la méthode init(), les méthodes peuvent avoir un nombre arbitraire
d'arguments.

Exemple un peu plus complet : ::

    from nucentral import Component

    class MonComposant(Component):
        NAME = "mon_composant"
        VERSION = "1.0"
        API_VERSION = 1

        def service_foo(self, data):
            return data

        def page_test(self):
            # Page "test"
            ...

Enregistrer le composant
========================

Pour enregistrer le composant, ajoutez un ligne « nom = yes » dans votre
fichier de configuration NuCentral (typiquement,
/etc/nucentral/nucentral.conf) : ::

    [modules]
    mon_composant = yes

Il est également possible de faire un lien symbolique du fichier du composant
dans le repertoire /var/lib/nucentral/mods-enabled/, qui chargera le composant
au lancement de nucentral automatiquement.

Tester le composant
===================

Relancez NuCentral, puis testez votre service avec tools/simple_client.py.
Exemple avec le composant foo et son service print : ::

    $ ./simple_client.py
    NuCentral status: up and running
    Type "help" for more information.
    >> explore
    ...
    [+] foo
            fire
            delCallback
            addCallback
            print
            error
    ...
    >> foo print
    Hello, world

