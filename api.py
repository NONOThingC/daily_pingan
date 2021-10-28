import requests
import base64
class GET_CAPTCHA:
    
    def __init__(self,username,passwd) -> None:
        r=requests.get("http://api.95man.com:8888/api/Http/UserTaken?user="+str(username)+"&pwd="+str(passwd)+"&isref=0")
        res=r.text.strip().split("|")
        r.close()
        if int(res[0])==1:
            self.user_tokens=res[1]
        else:
            print("get user tokens fail.")
            exit(0)
        
        
        
    def get_captcha_from_api(self,image_data):
        len_captcha=4
        type_captcha=str("1")
        api_url="http://api.95man.com:8888/api/Http/Recog?Taken="+self.user_tokens+"&len="+str(len_captcha)+"&imgtype="+str(type_captcha)
        # api_url="http://api.95man.com:8888/api/Http/Recog?Taken="+user_tokens+"&len="+str(len_captcha)
        """
        参数说明：

        Taken：用户taken

        imgtype：验证码类型,可登录平台首页查看，不填默认为通用类型，查看类型

        len：指定返回长度,如果图片验证码是4位，这里可以指定为4，能提高一定精度，也可以不指定。注意若因指定错误造成的识别错误，如验证码是5位，指定为4，则最多返回4位，而造成的识别错误，平台不审核，不返分。

        angle：图片旋转角度，默认为0，不旋转。负数表示逆时针旋转，正数表示顺时针旋转，如angle=-90，表示逆时针旋转90度，angle=90，表示顺时针旋转90度，角度可以是任意角度。

        以下图片参数必选其一,用POST方法提交，其他参数跟在URL地址后面

        ImgBase64=图片数据base64字符串（部分编程语言提交前需Html编码），注意提交是用传统的POST表单格式提交，不是json格式。

        imgfile=图片文件二进制流(或是称之为内存流,文件流) 就是普通网页上传文件的方式，采用这种方式"ImgBase64"就不填，否则采用"ImgBase64"的值

        成功返回：

        格式为：图片ID|识别结果|用户余额 。用“|”隔开 如：49|dksr|18 。可判断前面的数字是否大于0，大于0则表示成功。
        """

        # with open('code.png', 'rb') as f:
        #     img_bytes = f.read()
        # data={
        #     "ImgBase64":base64.b64encode(img_bytes).decode()
        # }
        data={
            "ImgBase64":base64.b64encode(image_data).decode()
        }
        rep=requests.post(api_url,data=data)
        reg_res=rep.text.strip().split("|")
        if int(reg_res[0])<0:
            # handle error
            print(reg_res)
        else:
            captcha_content=reg_res[1]
            print(captcha_content)
            return captcha_content