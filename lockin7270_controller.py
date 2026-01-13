import time
import pyvisa

class InstrumentLockin7270:

    SENSITIVITY_SCALE= {
        1: 2.0e-9, 2: 5.0e-9, 3: 10.0e-9, 4: 20.0e-9, 5: 50.0e-9, 6: 100.0e-9,
        7: 200.0e-9, 8: 500.0e-9, 9: 1.0e-6, 10: 2.0e-6, 11: 5.0e-6, 12: 10.0e-6,
        13: 20.0e-6, 14: 50.0e-6, 15: 100.0e-6, 16: 200.0e-6, 17: 500.0e-6, 18: 1.0e-3,
        19: 2.0e-3, 20: 5.0e-3, 21: 10.0e-3, 22: 20.0e-3, 23: 50.0e-3, 24: 100.0e-3,
        25: 200.0e-3, 26: 500.0e-3, 27: 1.0
    }

    def __init__(self, s_ip_address):
        self.rm = pyvisa.ResourceManager('C:/Windows/System32/visa32.dll')  # 32 bit windows
        self.inst = self._connection_open_ethernet(s_ip_address)

    def _connection_open_ethernet(self, s_ip_address):
        """
            通过Ethernet开启与仪器的连接。

            参数:
                s_ip_address (str): 仪器的IP地址。

            返回:
                object: 如果成功则返回仪器的连接实例，否则返回None。
           """
        try:
            # 验证IP地址格式（这只是一个基本的验证，可能不足以捕获所有无效的输入）
            ip_parts = s_ip_address.split('.')
            if len(ip_parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                print(f"错误: 无效的IP地址 - {s_ip_address}")
                return None

            print('通过Ethernet开启连接...')
            inst = self.rm.open_resource('TCPIP0::' + s_ip_address + '::50001::SOCKET')
            return inst

        except Exception as e:
            print(f"打开连接时出错: {e}")
            return None
        # 使用 self.rm 替代 rm, 返回 inst 而不是将其设置为属性

    def _query_device(self, cdm, retries=10, delay=3):
        for attempt in range(retries):
            self.inst.clear()
            time.sleep(0.1)
            print(f'Send query command: {cdm}')
            self.inst.write_raw(cdm + '\r')
            time.sleep(1)  # Wait for 100 milliseconds

            response = ''
            while True:
                try:
                    char = self.inst.read_bytes(1).decode('utf8')
                    if char == '\0' or char == '\r':
                        break
                    response += char
                    time.sleep(0.05)
                except pyvisa.errors.VisaIOError as e:
                    if e.error_code == pyvisa.constants.StatusCode.error_timeout:
                        print('Read timeout, retrying...')
                        time.sleep(0.05)
                        continue  # If timeout, continue trying to read
                    else:
                        raise  # If it's another error, raise the exception

            print(f'Raw Response: {response}')  # Debug: Print raw response string
            self.inst.clear()
            if response:  # Check if response is not empty
                return response
            else:
                print(f'No response, retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})')
                time.sleep(delay)

        print(f'Error: No response from device after {retries} attempts')
        return response
        # 使用 self.inst 替代 inst

    # 文件名: lockin7270_controller.py
# 在 InstrumentLockin7270 类中添加以下方法

    def set_harmonic(self, harmonic_order):
        """
        设置锁相放大器的检测谐波次数。
        为了复现论文 Fig. 1e/f，需要设置为 2 (2nd Harmonic)。
        
        参数:
            harmonic_order (int): 1 表示基频 (1f), 2 表示倍频 (2f) 等。
        """
        try:
            # 注意：Signal Recovery 7270 的具体谐波指令通常是 'IE' 或 'REFN'。
            # 下面使用的是常见指令格式，如果无效，请查阅 7270 手册查找 "Reference Harmonic" 指令。
            # 假设指令为 IE <n> (0=1f, 1=2f...) 或者直接 REFN <n>
            
            # 示例逻辑：根据具体仪器指令集调整字符串
            command = f'REFN {harmonic_order}' 
            
            print(f'Setting harmonic detection to: {harmonic_order}omega')
            self.inst.write_raw(command + '\r')
            time.sleep(1) # 等待设置生效
        except Exception as e:
            print(f"设置谐波次数时出错: {e}")

    def set_reference_phase(self, phase):
        """
        设置参考相位 (可选，用于对齐信号)。
        """
        try:
            command = f'PHA {phase}'
            self.inst.write_raw(command + '\r')
        except Exception as e:
            print(f"设置相位出错: {e}")
    
    def query_voltage1(self):
        return self._query_device(cdm='MAG1. ')

    def query_voltage2(self):
        return self._query_device(cdm='MAG2. ')

    def query_sensitivity1(self):
    # 7270 的 SEN 查询通常返回档位编号(1~27)，这里映射成满量程电压 FS (V)
        key = int(float(self._query_device(cdm='SEN1. ')))
        return self.SENSITIVITY_SCALE[key]

    def query_sensitivity2(self):
        key = int(float(self._query_device(cdm='SEN2. ')))
        return self.SENSITIVITY_SCALE[key]

    def query_phase1(self):
        return self._query_device(cdm='PHA1. ')

    def query_phase2(self):
        return self._query_device(cdm='PHA2. ')

    def _get_suitable_key(self, target_value):
        suitable_keys = [key for key, value in self.SENSITIVITY_SCALE.items() if value < target_value]
        if not suitable_keys:
            raise ValueError('Error: No suitable sensitivity found')
        return max(suitable_keys)

    def adjust_sensitivity(self, sen_function, query_function, cmd_prefix, max_attempts=3,
                       low_ratio=0.10, high_ratio=0.90, settle_time=1.0):
        """
    自动调整灵敏度(SEN)，让信号幅值落在 [low_ratio, high_ratio] * FS 范围内。
    注意：这里假设 sen_function() 返回的是满量程电压 FS (V)，
         所以 query_sensitivity1/2 需要做 key->FS 映射（上面已给出）。
    """
        attempts = 0

        # 按 FS 从小到大排序
        scale_items = sorted(self.SENSITIVITY_SCALE.items(), key=lambda kv: kv[1])
        min_key, min_fs = scale_items[0]
        max_key, max_fs = scale_items[-1]

        while attempts < max_attempts:
            target_value = float(query_function())   # e.g. MAG1 (V)
            current_fs = float(sen_function())       # FS (V)

            # 当前档位已合适
            if (low_ratio * current_fs) <= target_value <= (high_ratio * current_fs):
                print("Current sensitivity setting is appropriate for the target value.")
                return

            # 选择合适档位：选最小的 FS，使 target_value <= high_ratio * FS
            if target_value <= (low_ratio * min_fs):
                suitable_key = min_key
            elif target_value >= (high_ratio * max_fs):
                suitable_key = max_key
            else:
                suitable_key = None
                for k, fs in scale_items:
                    if target_value <= (high_ratio * fs):
                        suitable_key = k
                        break
                if suitable_key is None:
                    suitable_key = max_key

            command = f"{cmd_prefix.strip()} {suitable_key}"
            print(f"Send set sensitivity command: {command}")
            self.inst.clear()
            time.sleep(0.05)
            self.inst.write_raw(command + "\r")
            time.sleep(settle_time)  # 原来 60s 太长，这里默认 1s，可按 time constant 调大

            # 验证设置是否合理
            updated_fs = float(sen_function())
            updated_value = float(query_function())
            print(f"Updated sensitivity FS: {updated_fs}, Updated value: {updated_value}")

            if (low_ratio * updated_fs) <= updated_value <= (high_ratio * updated_fs):
                print("Updated sensitivity setting is appropriate for the updated value.")
                return

            print(f"Warning: SEN may be suboptimal; value={updated_value} FS={updated_fs}")
            attempts += 1

    print("Warning: Unable to find suitable sensitivity setting after multiple attempts.")

    def set_sensitivity1(self, max_attempts=3):
        self.adjust_sensitivity(self.query_sensitivity1, self.query_voltage1, 'SEN1 ', max_attempts)

    def set_sensitivity2(self, max_attempts=3):
        self.adjust_sensitivity(self.query_sensitivity2, self.query_voltage2, 'SEN2 ', max_attempts)

    def disable_automatic_acgain(self):
        """Disables the automatic AC gain."""
        self.inst.write_raw("AUTOMATIC 0" +'\r')
        time.sleep(1)

    def query_acgain(self):
       return self._query_device(cdm='ACGAIN')

    def set_acgain(self, gain_key):
        """Sets the AC gain to the provided key value."""
        command = f"ACGAIN {gain_key}"+'\r'
        print(command)
        self.inst.write_raw(command)
        time.sleep(1)

    def optimize_acgain(self):
        """Optimizes the AC gain."""
        self.disable_automatic_acgain()
        current_gain_key = self.query_acgain()
        optimized_gain_key = int(current_gain_key) + 5
        if optimized_gain_key>11:
            self.set_acgain(11)
        else:
            self.set_acgain(optimized_gain_key)
        time.sleep(1)


    def set_automatic_acgain(self):
        """
            开启仪器的 ACGAIN 自动调整。

            参数:
                inst (object): 仪器的连接实例。
            """
        try:
            print('开启 ACGAIN 自动调整...')
            self.inst.clear()
            time.sleep(0.05)
            self.inst.write_raw('AUTOMATIC 1\r')
            time.sleep(1)  # 等待一会儿以确保命令已经生效
            print('ACGAIN 自动调整已开启')
        except Exception as e:
            print(f"设置 ACGAIN 自动调整时出错: {e}")
        # 使用 self.inst 替代 inst

# 使用示例:
# if __name__ == "__main__":
#     controller = InstrumentLockin7270('192.168.1.1')
#     voltage1 = controller.query_voltage1()
#     print(voltage1)