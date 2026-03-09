

from backend.app import injector_obj_list
from fpxh_control_sdk.electrolyte_lab.fpxh_control.core import InjectionController

def equipment_start(arg_dict, startLandian, process_json_str):
    # 创建实例测试
    try:
        #mysql -h 101.6.160.48 -P 50003 -u landian -p123456 electrolyte
        injector = InjectionController(arg_dict,use_mysql=True,
                                    host_mysql="101.6.160.48", user_mysql="landian", password_mysql="123456",
                                    port_mysql=50003, db_mysql="electrolyte",FAKE_MODE=True,start_landian=startLandian,process_json_str=process_json_str
                                    )
    except Exception as e:
        print(f"无法设备初始化: {str(e)}")
        return False
    else:
        try:
            if not injector.FAKE_MODE:
                if not injector.is_idle():  #运行前判定机器是否空闲
                    raise Exception("请等待所有实验结束")
            injector_obj_list.append(injector)
            injector.start()

        except Exception as e:
            print(f"机器不空闲，无法开始实验: {str(e)}")
            return False
        else:
            return True
            
