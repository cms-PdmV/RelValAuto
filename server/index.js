const express = require("express");
const app = express();

var fs = require("fs");
var os = require("os");

// Middleware for Express.js
app.use(express.json());
app.use(express.urlencoded());

function endInput() {
  if (confirm("Save form input and Close Window?")) {
    close();
  }
}

app.get("/", function (request, response, next) {
  response.send(`
        <head>
        <script src="http://code.jquery.com/jquery-git2.js"></script>        
        <meta http-equiv="content-type" content="text/html; charset=windows-1252">

            <title>Tickets updating tool</title>
            <style>
            table {
            border-collapse:collapse;
            }
            table,th, td {
            border: 1px solid black;
            }
            .txt {
            font-weight:bold;
            text-align:right;
            }
            .phone {
            font-weight:bold;
            text-align:right;
            width:150px;
            }
            .footer {
            text-align:center;
            padding:5px;
            background-color:lightblue;
            }
            .city {
            width:180px;
            }
            .state {
            width:50px;
            }
            </style>
        </head>
        <body>
            <form method="POST" action="/">
                <table>
                <tbody>
                <tr>
                    <th class="txt" style="width:200px"><label for="cmssw_release">CMSSW release</label></th>
                    <td colspan="3"><input type="text" id="cmssw_release" name="cmssw_release" placeholder="12_5_0_pre1" tabindex="1" style="width:270px;"></td>
                </tr>

                <tr>
                    <th class="txt"><label for="batch_name">Batch name</label></th>
                    <td colspan="3"><input type="text" id="batch_name" name="batch_name" placeholder="fullsim_PU_2022_14TeV" tabindex="2" style="width:270px"></td>
                </tr>

                <tr>
                    <th class="txt">Add these workflow IDs</th>
                    <td colspan="3"><textarea id="workflow_ids_add" name="workflow_ids_add" placeholder="39408 &#10;39409 &#10;39434 &#10;39436" rows="5" cols="30"  tabindex="3"></textarea></td>
                </tr>
                
                <tr>
                    <th class="txt">Remove these workflow IDs</th>
                    <td colspan="3"><textarea id="workflow_ids_remove" name="workflow_ids_remove" placeholder="11834 &#10;11846 &#10;11892 &#10;11852" rows="5" cols="30"  tabindex="4"></textarea></td>
                </tr>

                <tr>
                    <th class="txt"><label for="n_factor">Events factor</label> </th>
                    <td colspan="3"><input type="number" id="n_factor" name="n_factor" placeholder="1" tabindex="5" style="width:80px;"></td>
                </tr>

                <tr>
                    <th  class="city txt"><label for="recycle_gs">Recycle GS</label></th>
                    <td><input type="checkbox" id="recycle_gs" name="recycle_gs" tabindex="6"></td>
                </tr>

                <tr>
                    <th class="txt"><label for="rewrite_gt_string">Rewrite GT string</label></th>
                    <td colspan="3"><input type="rewrite_gt_string" id="rewrite_gt_string" name="rewrite_gt_string" placeholder="CMSSW_12_5_0_pre2-124X_mcRun3_2022_realistic_v3-v1" style="width:400px;" tabindex="7"></td>
                </tr>

                <tr>
                    <th colspan="4" class="footer">
                        <input id="next_ticket" type="submit" value="Next ticket" tabindex="8" style="background-color:yellow">
                        <input id="finish_input" type="submit" onclick="window.close()" value="Finish entire input" tabindex="9" style="background-color:lightgreen">
                        <input id="clear_input" type="reset" tabindex="10" style="background-color:red">
                    </th>				
                </tr>
            </tbody>
        </table>
            </form>
        </body>
    `);
});

app.post("/", function (request, response, next) {
  console.log("POST");
  console.log(request.body);
  fs.appendFile(
    "data.txt",
    JSON.stringify(request.body) + os.EOL,
    function (err) {
      if (err) throw err;
      console.log("Saved data to file");
    }
  );
});

app.listen(2000);
