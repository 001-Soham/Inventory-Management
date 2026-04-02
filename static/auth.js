function login(){
    fetch("/api/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            username:username.value,
            password:password.value
        })
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.error) alert(d.error)
        else window.location="/dashboard"
    })
}

function register(){
    fetch("/api/register",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            username:username.value,
            password:password.value
        })
    })
    .then(r=>r.json())
    .then(d=>{
        alert(d.message || d.error)
        window.location="/login"
    })
}

function goRegister(){
    window.location="/register"
}
