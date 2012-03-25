<?php
$url = htmlspecialchars($_GET['url']);
$virus = $_GET['virus'];
$dest_bl = $_GET['dest_bl'];


$msg = <<< EOD
<p>The page ($url) you asked for is infected with a virus: $virus.<br/>
The request was blocked.</p>

<p>La page ($url) que vous avez demand&eacute;e est infect&eacute;e par un virus: $virus.<br />
La requ&ecirc;te est bloqu&eacute;e.</p>
EOD;

if (isset ($dest_bl)){
    $msg = "<p>The page ($url) you asked for is blocked because it is blacklisted.";
    if ($dest_bl != 'unknown') {
        $msg .= "<br />This page belongs to the category $dest_bl.";
    }
    $msg .= "</p>\n";

    $msg .= "<p>La page ($url) que vous avez demand&eacute;e est bloqu&eacute;e car elle est en liste noire.";
    if ($dest_bl != 'unknown') {
        $msg .= "<br />Cette page appartient &agrave; la cat&eacute;gorie $dest_bl.";
    }
    $msg .= "</p>\n";
}
?>

<html>
 <head>
  <title>EdenWall Information Page</title>
<style type="text/css">
/* CSS for nuconf */
body{
    margin-top:0;
    background-color: white;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 90%;
    max-width: 850px;
}

h1{
    margin-top:0;
    padding-left:5px;
    margin-bottom: 0;
    border-right: #a7a7a7 solid thin;
    background-color: rgb(122,180,29);
    color:white;
    font-size: 130%;
    padding-top:2px;
    padding-bottom:2px;
}

h2 {
    border-left: none;
    border-top: none;
    background: rgb(240, 240, 240);
    border-bottom: none;
    margin-bottom: 0;
    color: #535a72;
    padding-left: 10px;
    margin-right: 20%;
    background-color: rgb(78,127,167);
    color:white;
    font-size: 110%;
}

h3.intable{
    font-size: smaller;
}

/* Start block display */

div#main:after {
    content: "";
    display: block;
    clear: both;
}

div#main, body.body {
    float: left;
    width: 720px;
    margin-left: 10px;
    margin-top: 10px;
    min-height: 500px;
    border-left: #a7a7a7 dashed thin;
    background-color:white;
    background-color: rgb(78,127,167);
    padding:10px;
}

div#copyright{
    text-align:center;
    font-size: smaller;
    color: #686868;
    width: 100%;
    float: left;
    margin-top:10px;
    margin-bottom:5px;
}

div#leftmenu {
    margin-top: 70px;
}

/* End block display */

</style>
 </head>
 <body>
  <h1>EdenWall Information</h1>
  <?php print $msg; ?>
 </body>
</html>

