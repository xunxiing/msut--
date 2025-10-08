# --- 1. 输入参数 (Inputs) ---

# 核心控制目标与设定
controlled_object = INPUT(attrs={"name": "Object", "data_type": 1})
target_position = INPUT(attrs={"name": "TargetPosition", "data_type": 8})

# Y轴 PID增益
kp = INPUT(attrs={"name": "Kp", "data_type": 2})
ki = INPUT(attrs={"name": "Ki", "data_type": 2})
kd = INPUT(attrs={"name": "Kd", "data_type": 2})

# 新增：动态刹车系统参数
brake_activation_distance = INPUT(attrs={"name": "BrakeDistance", "data_type": 2, "value": 5.0})
brake_aggression = INPUT(attrs={"name": "BrakeAggression", "data_type": 2}) # 刹车力度和速度上限的调整因子

# 物理环境设定
gravity_acceleration = INPUT(attrs={"name": "Gravity", "data_type": 2, "value": 9.8})
reset_integral = INPUT(attrs={"name": "ResetIntegral", "data_type": 2})

# --- 2. 常量与时间 (Constants & Time) ---
const_time = TIME()
const_zero = Constant(attrs={"value": 0.0})
const_neg_one = Constant(attrs={"value": -1.0})

# --- 3. 传感器与向量分解 (Sensors & Vector Deconstruction) ---
current_pos_node = Position(object=controlled_object["OUTPUT"])
current_vel_node = Velocity(object=controlled_object["OUTPUT"])
object_mass = MASS(Entity=controlled_object["OUTPUT"])

target_pos_split = Split(Vector=target_position["OUTPUT"])
current_pos_split = Split(Vector=current_pos_node["Position"])
current_vel_split = Split(Vector=current_vel_node["Velocity"])

# --- 4. 基础计算：PID 与 重力补偿 (Base Calculations: PID & Gravity) ---
# Y轴误差
pos_error_y = SUBTRACT(A=target_pos_split["Y"], B=current_pos_split["Y"])
# P, I, D 项计算...
p_force_y = MULTIPLY(A=pos_error_y["A-B"], B=kp["OUTPUT"])
error_y_dt = MULTIPLY(A=pos_error_y["A-B"], B=const_time["DELTA TIME"])
integral_accumulator_y = ACCUMULATOR(NUMBER=error_y_dt["A*B"], RESET=reset_integral["OUTPUT"])
i_force_y = MULTIPLY(A=integral_accumulator_y["RESULT"], B=ki["OUTPUT"])
d_force_y = MULTIPLY(A=current_vel_split["Y"], B=kd["OUTPUT"])
# 组合PID修正力
pi_force_y = ADD(A=p_force_y["A*B"], B=i_force_y["A*B"])
pid_corrective_force_y = SUBTRACT(A=pi_force_y["A+B"], B=d_force_y["A*B"])
# 重力补偿力
gravity_comp_force = MULTIPLY(A=object_mass["Mass"], B=gravity_acceleration["OUTPUT"])
# 基础总力 (PID + 重力)
base_total_force_y = ADD(A=pid_corrective_force_y["A-B"], B=gravity_comp_force["A*B"])

# --- 5. 核心升级：动态刹车系统 (CORE UPGRADE: Dynamic Braking System) ---
# 5.1 计算绝对距离并判断是否进入刹车区
abs_error_y = ABS(A=pos_error_y["A-B"])
is_in_braking_zone = LESS_THAN(A=abs_error_y["abs(A)"], B=brake_activation_distance["OUTPUT"])

# 5.2 计算动态速度上限 (dynamic_max_speed = distance^2 * aggression_factor)
error_squared = SQUARE(A=abs_error_y["abs(A)"])
dynamic_max_speed = MULTIPLY(A=error_squared["A*A"], B=brake_aggression["OUTPUT"])

# 5.3 判断是否超速
abs_current_speed_y = ABS(A=current_vel_split["Y"])
is_overspeeding = GREATER_THAN(A=abs_current_speed_y["abs(A)"], B=dynamic_max_speed["A*B"])

# 5.4 确定是否需要施加主动刹车 (必须同时在刹车区内且超速)
should_apply_brake = AND(A=is_in_braking_zone["A < B"], B=is_overspeeding["A > B"])

# 5.5 计算主动刹车力
# 刹车力与当前速度成正比，方向相反，力度由BrakeAggression调节
# BrakeForce = -current_velocity * BrakeAggression
braking_force_unsigned = MULTIPLY(A=current_vel_split["Y"], B=brake_aggression["OUTPUT"])
active_braking_force = MULTIPLY(A=braking_force_unsigned["A*B"], B=const_neg_one["OUT"])

# 5.6 选择是否应用刹车力
final_extra_brake_force = branch(IF=should_apply_brake["A AND B"], A=active_braking_force["A*B"], B=const_zero["OUT"])

# --- 6. 最终力合成与输出 (Final Force Composition & Output) ---
# 最终力 = (PID修正力 + 重力补偿力) + 主动刹车力
total_force_y = ADD(A=base_total_force_y["A+B"], B=final_extra_brake_force["result"])

# 组合成最终的力向量
final_force_vector = Combine(X=const_zero["OUT"], Y=total_force_y["A+B"], Z=const_zero["OUT"], W=const_zero["OUT"])

# 主输出
force_output = OUTPUT(INPUT=final_force_vector["Vector"], attrs={"name": "Force", "data_type": 8})

# 调试输出
debug_should_brake = OUTPUT(INPUT=should_apply_brake["A AND B"], attrs={"name": "DebugIsBraking", "data_type": 2})
debug_dynamic_max_speed = OUTPUT(INPUT=dynamic_max_speed["A*B"], attrs={"name": "DebugMaxSpeed", "data_type": 2})
debug_braking_force = OUTPUT(INPUT=final_extra_brake_force["result"], attrs={"name": "DebugBrakeForce", "data_type": 2})