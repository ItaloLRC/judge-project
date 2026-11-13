"use strict";

const API = ""

function OnButtonClick(){

    let text = document.getElementById("txtarea1").value;
    let inputText = document.getElementById("inputarea").value;
    let textLanguage = document.getElementById("langarea").value;

    console.log(inputText)
    console.log(textLanguage);
    console.log(API + "/submit");
    
    fetch(API + "/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json"},
            body: JSON.stringify({input: inputText, code: text, lang: textLanguage})
        }).then(function(ans){
            if (!ans.ok) {
                throw new Error("Falha na submissão");
            }
            return ans.json();
        }).then(function(data){
            console.log(data);

            if(data.flag){
                document.getElementById("txtarea2").value = data.errout;
                console.log(data.errout);
            }
            else{
                document.getElementById("txtarea2").value = data.output;
                console.log(data.output)
            }
        }).catch(function(error){
            document.getElementById("txtarea2").value = "Erro de envio!";
            console.log("Erro de envio.");
        })
    
}


document.getElementById("botao1").addEventListener("click", OnButtonClick);
