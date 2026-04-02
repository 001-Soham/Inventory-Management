function loadItems(){
    fetch("/api/items")
    .then(r=>r.json())
    .then(data=>{
        items.innerHTML=""
        data.forEach(i=>{
            items.innerHTML += `
                <div class="item">
                    ${i.name} - ${i.quantity}
                    <button onclick="del(${i.id})">X</button>
                </div>
            `
        })
    })
}

function addItem(){
    fetch("/api/items",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            name:name.value,
            quantity:qty.value
        })
    }).then(()=>loadItems())
}

function del(id){
    fetch("/api/items/"+id,{method:"DELETE"})
    .then(()=>loadItems())
}

loadItems()
