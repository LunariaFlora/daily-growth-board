using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;
class Launch {
  [STAThread] static void Main() {
    try {
      string root=AppDomain.CurrentDomain.BaseDirectory;
      if(!File.Exists(Path.Combine(root,"bootstrap.ps1")))throw new Exception("请先完整解压文件夹，再双击日有所积.exe。");
      var start=new ProcessStartInfo("powershell.exe", "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \""+Path.Combine(root,"bootstrap.ps1")+"\"");
      start.WorkingDirectory=root;start.UseShellExecute=false;start.CreateNoWindow=true;
      Process.Start(start);
    } catch(Exception e) { MessageBox.Show(e.Message,"日有所积 · 启动失败"); }
  }
}
