

console.log('js파일 로드')
function load_detail(photo_id) {
  alert('load detail')
  console.log('load detail 실행')
  url = window.location.host+"/detail/" + photo_id;
  window = location.href = url;
}

function tag_adder() {
  // alert("멈춰1");
  console.log("function tag_adder 실행");
      let csrftoken =null;
  try {
    csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
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
    photo_id = parseInt(photo_id[photo_id.length - 1]);
    console.log(photo_id);
  } catch {
    console.log("photo 실패");
  }

  $.ajax({
    type: "POST",
    url: "add_tag/",
    // async:false,
    dataType: "json",
    data: {
      photo: photo_id,
      tags: tag,
      csrfmiddlewaretoken:csrftoken
    },
    success: function (response) {
      console.log(response);
      // alert("성공");
      
  location.reload(true)
    // $("#tags_div").load(location.href);
      console.log("통신 success");
    },
    error: function () {
      console.log(response);
      // alert('에러');
      console.log("error");
    },
    complete: function () {
      console.log(response);
      // alert('완료')
      console.log("complete");
    },
  });
  // location.replace(location.href);
  // location.reload(true)
  // history.go(0);
  // location.href = location.href;
  // $("#tags_div").load(location.href);
  // $("#tags_div").load(window.document.href);
  // window.document.href=window.document.href
  // 출처: https://offbyone.tistory.com/235 [쉬고 싶은 개발자:티스토리]
  // 출처: https://7942yongdae.tistory.com/53 [프로그래머 YD:티스토리]
  
//   setTimeout(function () {
//     location.reload()
//     // alert('page is loaded and 1 minute has passed');
// }, 100);
}
