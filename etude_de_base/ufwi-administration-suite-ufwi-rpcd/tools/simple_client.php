#!/usr/bin/env php
<?php
# Copyright(C) 2008 INL
# Written by Victor Stinner <victor.stinner AT inl.fr>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# $Id$
# ----------
# PHP5 command line program

define('PROTOCOL_VERSION', '0.1');
define('CLIENT_NAME', 'simple_client.php');
define('CLIENT_VERSION', '0.5');

class NuCentralClient
{
    function NuCentralClient($host, $protocol='https', $port=NULL)
    {
        if (!isset($port)) {
            if ($protocol == 'http')
                $port = 8080;
            else
                $port = 8443;
        }
        $this->server_url = "$protocol://$host:$port/RPC2";
        $this->cookie = '';
        $this->createSession();
    }

    function callService($component, $service, $arguments=Array())
    {
        // Call XML-RPC method
        $arguments = array_merge(Array($this->cookie, $component, $service) , $arguments);
        $data = $this->xmlrpcCall('callService_s', $arguments);

        // Parse result
        $data = xmlrpc_decode($data);

        // XML-RPC error?
        if (is_array($data)
            and array_key_exists('faultCode', $data)
            and array_key_exists('faultString', $data))
        {
            throw new Exception(sprintf('XML-RPC error (%s): %s',
                $data['faultCode'], $data['faultString']));
        }

        // Parse NuCentral result
        $result = $data[1];
        if (is_array($result) and array_key_exists('result', $result)) {
            $result = $result['result'];
        }

        // NuCentral error?
        if ($data[0]) {
            if (array_key_exists('message', $result)) {
                $message = $result['message'];
            } else {
                $message = vsprintf($result['format'], $result['arguments']);
            }
            throw new Exception($message);
        }
        return $result;
    }

    function logout()
    {
        if ($this->cookie == '')
            return;
        $this->callService('session', 'destroySession');
        $this->cookie = '';
    }

    private function createSession()
    {
        try {
            $args = Array(Array(
                'client_name' => CLIENT_NAME,
                'client_release' => CLIENT_VERSION,
                'protocol_version' => PROTOCOL_VERSION,
            ));
            $result = $this->callService('CORE', 'createSession', $args);
        } catch (Exception $err) {
            # clientHello() doesn't support client_release field
            $result = $this->callService('CORE', 'clientHello', Array(CLIENT_NAME, PROTOCOL_VERSION));
        }
        # $result is an array: Array(server_version, cookie)
        $this->cookie = $result[1];
    }

    function xmlrpcCall($method, $params)
    {
        $request = xmlrpc_encode_request('callService', $params);

        $header[] = "Content-type: text/xml";
        $header[] = "Content-length: ".strlen($request);

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $this->server_url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_TIMEOUT, 1);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $header);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $request);

        $data = curl_exec($ch);
        if (curl_errno($ch)) {
            print curl_error($ch);
        } else {
            curl_close($ch);
            return $data;
        }
    }

    function authenticate($login, $password)
    {
        return $this->callService('session', 'authenticate', Array($login, $password));
    }
}

error_reporting(E_ALL);
if (count($argv) < 5) {
    echo sprintf("Usage: %s login password component service [arg1 arg2 ...]\n", $argv[0]);
    exit(1);
}

$login = $argv[1];
$password = $argv[2];
$component = $argv[3];
$service = $argv[4];
$service_arguments = array_slice($argv, 5);

$host = 'localhost';
$protocol = 'http';
$port = 8080;
$client = new NuCentralClient($host, $protocol, $port);
try {
    $client->authenticate($login, $password);
    $result = $client->callService($component, $service, $service_arguments);
    echo "Result:\n---\n";
    var_dump($result);
    echo "---\n";
} catch (Exception $err) {
    echo sprintf("ERROR: %s\n", $err->getMessage());
}
?>
