# client.py
import asyncio
import os
import sys
import time
import tenseal as ts
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ==========================================
DEEPSEEK_API_KEY = "sk-42093b20de734fd18e2c59ce74ea1867"
BASE_URL = "https://api.deepseek.com"

client_ai = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)
server_params = StdioServerParameters(command=sys.executable, args=["server.py"], env=None)


def setup_context():
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=16384,
        coeff_mod_bit_sizes=[60, 40, 40, 40, 40, 40, 60]
    )
    context.global_scale = 2 ** 40
    context.generate_galois_keys()
    return context


def encrypt_and_save(context, data, filename):
    enc_vec = ts.ckks_vector(context, data)
    path = os.path.abspath(filename)
    with open(path, "wb") as f:
        f.write(enc_vec.serialize())
    return path


async def run_chat_loop():
    print(f"{'=' * 40}")
    print("🚀 Starting Parallel Privacy Computing Task")
    print(f"{'=' * 40}\n")

    # --- 阶段 1: 客户端本地加密 ---
    print("🔹 Phase 1: Local Encryption...")
    t_start_enc = time.perf_counter()

    try:
        local_ctx = setup_context()
        uwb_raw = [0.8, 1.2, 0.5]
        imu_raw = [0.5, 0.2, 9.81, 0.1, -0.1, 0.5]

        # 写入文件
        pub_ctx = local_ctx.copy()
        pub_ctx.make_context_public()
        ctx_path = os.path.abspath("pub_ctx.ts")
        with open(ctx_path, "wb") as f:
            f.write(pub_ctx.serialize())

        uwb_path = encrypt_and_save(local_ctx, uwb_raw, "input_uwb.enc")
        imu_path = encrypt_and_save(local_ctx, imu_raw, "input_imu.enc")

        uwb_out_path = os.path.abspath("result_uwb.enc")
        imu_out_path = os.path.abspath("result_imu.enc")

    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        return

    t_end_enc = time.perf_counter()
    duration_enc = t_end_enc - t_start_enc
    print(f"✅ Encryption Done. (Context N=16384)")

    # 建立 MCP 连接
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            deepseek_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            } for tool in tools.tools]

            user_query = (
                f"并行处理以下加密任务："
                f"1. 公钥: {ctx_path}\n"
                f"2. UWB数据: {uwb_path} -> 输出 {uwb_out_path}\n"
                f"3. IMU数据: {imu_path} -> 输出 {imu_out_path}\n"
            )

            messages = [
                {"role": "system", "content": "You are a scheduler. Always call tools in parallel when possible."},
                {"role": "user", "content": user_query}
            ]

            # --- 阶段 2: 大模型任务分发 ---
            print("\n🔹 Phase 2: LLM Task Dispatching...")
            t_start_llm = time.perf_counter()

            response = await client_ai.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=deepseek_tools
            )

            t_end_llm = time.perf_counter()
            duration_llm = t_end_llm - t_start_llm

            response_msg = response.choices[0].message

            # --- 阶段 3: 并行工具计算 ---
            duration_compute = 0.0

            if response_msg.tool_calls:
                task_count = len(response_msg.tool_calls)
                print(f"✅ AI Dispatch Done. Scheduled {task_count} tasks.")
                print(f"\n🔹 Phase 3: Parallel Tool Execution...")

                t_start_compute = time.perf_counter()

                # 1. 创建任务列表
                mcp_tasks = []
                tool_names = []

                for tool_call in response_msg.tool_calls:
                    fn_name = tool_call.function.name
                    args = eval(tool_call.function.arguments)
                    tool_names.append(fn_name)
                    print(f" -> Scheduled: {fn_name}")

                    # 创建 coroutine 但不立即 await
                    mcp_tasks.append(session.call_tool(fn_name, arguments=args))

                # 2. 并行执行 (Parallel Execution)
                # asyncio.gather 会并发发送请求
                results = await asyncio.gather(*mcp_tasks)

                t_end_compute = time.perf_counter()
                duration_compute = t_end_compute - t_start_compute

                print("✅ Parallel Execution Complete.")

                # 验证结果
                print("\n🔹 Phase 4: Final Decryption & Verification")
                if os.path.exists(uwb_out_path):
                    res = ts.ckks_vector_from(local_ctx, open(uwb_out_path, "rb").read())
                    print(f"   UWB Decrypted: {res.decrypt()[0]:.4f}")

                if os.path.exists(imu_out_path):
                    res = ts.ckks_vector_from(local_ctx, open(imu_out_path, "rb").read())
                    print(f"   IMU Decrypted: {res.decrypt()[0]:.4f}")

            else:
                print("❌ AI did not schedule any tasks.")

            # --- 最终统计报告 ---
            print(f"\n{'-' * 40}")
            print("📊 Performance Statistics Report")
            print(f"{'-' * 40}")
            print(f"1. Encryption Time    : {duration_enc:.4f} sec")
            print(f"2. LLM Dispatch Time  : {duration_llm:.4f} sec")
            print(f"3. Toolbox Time (Par) : {duration_compute:.4f} sec")
            print(f"{'-' * 40}")
            print(f"Total Workflow Time   : {duration_enc + duration_llm + duration_compute:.4f} sec")
            print(f"{'-' * 40}")

    # Cleanup
    try:
        for p in [ctx_path, uwb_path, imu_path, uwb_out_path, imu_out_path]:
            if os.path.exists(p): os.remove(p)
    except:
        pass


if __name__ == "__main__":
    asyncio.run(run_chat_loop())