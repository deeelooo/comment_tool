var socket = io();

function commentOnParagraph(paragraph_id) {
    var country = prompt("Enter your country:");
    var io_ref = prompt("Enter the IO reference:");
    var comment = prompt("Enter your comment:");

    if (country && io_ref && comment) {
        $.post({
            url: '/submit_comment',
            contentType: 'application/json',
            data: JSON.stringify({
                'country': country,
                'paragraph_id': paragraph_id,
                'io_ref': io_ref,
                'comment': comment
            })
        });
    }
}

socket.on('new_comment', function (data) {
    var commentsDiv = document.getElementById('comments');
    var newCommentHTML = `
        <div>
            <strong>Country:</strong> ${data.country} |
            <strong>Paragraph:</strong> ${data.paragraph_id} |
            <strong>IO Ref:</strong> ${data.io_ref} |
            <strong>Comment:</strong> ${data.comment}
        </div><hr>
    `;
    commentsDiv.innerHTML += newCommentHTML;
});
