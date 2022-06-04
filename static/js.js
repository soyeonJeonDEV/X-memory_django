function load_detail(photo_id) {
  url = "detail/" + photo_id;
  window = location.href = url;
}

function tag_adder() {
  // alert("멈춰1");
  console.log("function tag_adder 실행");
      let csrftoken =null;
  try {
    csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    // alert(csrftoken )
    // console.log($("[name=csrfmiddlewaretoken]"))
    // let csrf_token = $("[name=csrfmiddlewaretoken]").val();
    // console.log(csrf_token);
  } catch {
    console.log("csrf실패");
  }
  // 태그값
  let tag = "";
  try {
    tag = $("#tagInput").val();
    console.log(tag);
  } catch {
    console.log("tag값검출 실패");
  }
// 사진아이디
  let photo_id = null;
  try {
    let url = window.location.href;
    console.log(url);
    photo_id = url.split("/");
    // console.log(photo_id);
    photo_id = photo_id[photo_id.length - 1];
    // console.log(photo_id);
    photo_id = parseInt(photo_id);
    console.log(photo_id);
  } catch {
    console.log("photo 실패");
  }

  $.ajax({
    type: "POST",
    url: "add_tag/",
    dataType: "json",
    data: {
      photo: photo_id,
      tags: tag,
      csrfmiddlewaretoken:csrftoken
      // csrfmiddlewaretoken: csrf_token,
    },
    // headers: { "X-CSRFToken": csrftoken },
    success: function (response) {
      console.log(response);
      alert("성공");
      console.log("success");
    },
    error: function () {
      console.log(response);
      alert('에러');
      console.log("error");
    },
    complete: function () {
      console.log(response);
      alert('완료')
      console.log("complete");
    },
  });
  // alert("멈춰2");
  // })
  // }
}

// function tag_adder(){
//   alert('멈춰');
//     console.log('function tag_adder 실행')
//     buttons= document.getElementsByClassName("tag");
//     console.log(buttons)
//     for(i=1;i<buttons.length;i++){
//       let a_button=buttons[i]
//       console.log(a_button)
//       a_button.addEventListener("click", function(e){
//         $.ajax({
//           type:"post",
//           url:"add_tag/",
//           dataType:"json",
//           data:{
//               photo:photo,
//               tags:tag,
//               csrfmiddlewaretoken: csrf_token,

//           },
//           headers: { "X-CSRFToken": "{{ csrf_token }}" },
//           success: function (response) {
//             console.log(response);
//             alert('멈춰');
//             console.log('success');
//           },
//           error: function () {
//             console.log("error");
//           },
//           complete: function () {
//             console.log('complete')
//           },
//         });

//       })
//     }
// }
